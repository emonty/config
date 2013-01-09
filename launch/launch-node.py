#!/usr/bin/env python

# Launch a new OpenStack project infrastructure node.

# Copyright (C) 2011-2012 OpenStack LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import commands
import time
import subprocess
import traceback
import socket
import argparse
import utils

NOVA_USERNAME=os.environ['OS_USERNAME']
NOVA_PASSWORD=os.environ['OS_PASSWORD']
NOVA_PROJECT_ID=os.environ['OS_TENANT_NAME']
NOVA_REGION_NAME=os.environ['OS_REGION_NAME']
OS_AUTH_SYSTEM=os.environ['OS_AUTH_SYSTEM']



SCRIPT_DIR = os.path.dirname(sys.argv[0])        

def get_client():
    import novaclient
    if OS_AUTH_SYSTEM and OS_AUTH_SYSTEM != 'keystone':
        os_auth_url = novaclient.client.get_auth_system_url(OS_AUTH_SYSTEM)
    else:
	os_auth_url = os.environ['OS_AUTH_URL']
    args = [NOVA_USERNAME, NOVA_PASSWORD, NOVA_PROJECT_ID, os_auth_url]
    kwargs = {}
    kwargs['region_name'] = NOVA_REGION_NAME
    kwargs['service_type'] = 'compute'
    from novaclient.v1_1.client import Client
    client = Client(*args, **kwargs)

    return client

def bootstrap_server(name, server, admin_pass, key, environment):
    client = server.manager.api
    ip = utils.get_public_ip(server)
    if not ip:
        raise Exception("Unable to find public ip of server")

    ssh_kwargs = {}
    if not key:
        ssh_kwargs['password'] = admin_pass

    for username in ['root', 'ubuntu']:
        ssh_client = utils.ssh_connect(ip, username, ssh_kwargs, timeout=600)
        if ssh_client: break

    if not ssh_client:
        raise Exception("Unable to log in via SSH")

    ssh_client.ssh('sudo hostname `curl http://169.254.169.254/2009-04-04/meta-data/hostname`' % name)

    if username != 'root':
        ssh_client.ssh("sudo cp ~/.ssh/authorized_keys"
                       " ~root/.ssh/authorized_keys")
        ssh_client.ssh("sudo chmod 644 ~root/.ssh/authorized_keys")
        ssh_client.ssh("sudo chown root.root ~root/.ssh/authorized_keys")

    ssh_client = utils.ssh_connect(ip, 'root', ssh_kwargs, timeout=600)

    ssh_client.ssh('git clone https://github.com/emonty/config')
    ssh_client.ssh('sudo bash -x config/install_modules.sh')

    ssh_client.ssh('sudo puppet apply'
                   ' --modulepath=`pwd`/config/modules:/etc/puppet/modules'
		   ' config/manifests/site.pp')

def build_server(client, name, image, flavor, environment):
    key = None
    server = None

    create_kwargs = dict(image=image, flavor=flavor, name=name)

    if 'os-keypairs' in utils.get_extensions(client):
        create_kwargs['key_name'] = 'mordred'
    server = client.servers.create(**create_kwargs)

    try:
        admin_pass = server.adminPass
        server = utils.wait_for_resource(server)
        bootstrap_server(name, server, admin_pass, key, environment)
    except Exception, real_error:
        try:
            utils.delete_server(server)
	    pass
        except Exception, delete_error:
            print "Exception encountered deleting server:"
            traceback.print_exc()
        # Raise the important exception that started this
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="server name")
    parser.add_argument("--ram", dest="ram", default=1024, type=int,
                        help="minimum amount of ram")
    parser.add_argument("--image", dest="image",
                        default="Ubuntu Quantal 12.10 Server 64-bit 20121017",
                        help="image name")
    parser.add_argument("--environment", dest="environment",
                        default="production",
                        help="puppet environment name")
    options = parser.parse_args()

    client = get_client()

    flavors = [f for f in client.flavors.list() if f.ram >= options.ram]
    flavors.sort(lambda a, b: cmp(a.ram, b.ram))
    flavor = flavors[0]
    print "Found flavor", flavor

    images = [i for i in client.images.list()
              if (options.image.lower() in i.name.lower() and
                not i.name.endswith('(Kernel)') and
                not i.name.endswith('(Ramdisk)'))]

    if len(images) > 1:
        print "Ambiguous image name; matches:"
        for i in images:
            print i.name
        sys.exit(1)

    if len(images) == 0:
        print "Unable to find matching image; image list:"
        for i in client.images.list():
            print i.name
        sys.exit(1)

    image = images[0]
    print "Found image", image

    build_server(client, options.name, image, flavor, options.environment)

if __name__ == '__main__':
    main()
