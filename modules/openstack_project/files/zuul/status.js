// Copyright 2012 OpenStack Foundation
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may
// not use this file except in compliance with the License. You may obtain
// a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
// WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
// License for the specific language governing permissions and limitations
// under the License.

window.zuul_enable_status_updates = true;

function format_pipeline(data) {
    var html = '<div class="pipeline"><h3 class="subhead">'+
        data['name']+'</h3>';
    if (data['description'] != null) {
        html += '<p>'+data['description']+'</p>';
    }

    $.each(data['change_queues'], function(change_queue_i, change_queue) {
        $.each(change_queue['heads'], function(head_i, head) {
            if (data['change_queues'].length > 1 && head_i == 0) {
                html += '<div> Change queue: ';

                var name = change_queue['name'];
                html += '<a title="' + name + '">';
                if (name.length > 32) {
                    name = name.substr(0,32) + '...';
                }
                html += name + '</a></div>'
            }
            $.each(head, function(change_i, change) {
                if (change_i > 0) {
                    html += '<div class="arrow">&uarr;</div>'
                }
                html += format_change(change);
            });
        });
    });

    html += '</div>';
    return html;
}

function format_change(change) {
    var html = '<div class="change"><div class="header">';

    html += '<span class="project">'+change['project']+'</span>';
    var id = change['id'];
    var url = change['url'];
    if (id.length == 40) {
        id = id.substr(0,7);
    }
    html += '<span class="changeid">';
    if (url != null) {
        html += '<a href="'+url+'">';
    }
    html += id;
    if (url != null) {
        html += '</a>';
    }
    html += '</span></div><div class="jobs">';

    $.each(change['jobs'], function(i, job) {
        result = job['result'];
        if (result == null) {
            result = 'unknown';
        }
        html += '<span class="job">';
        if (job['url'] != null) {
            html += '<a href="'+job['url']+'">';
        }
        html += job['name'];
        if (job['url'] != null) {
            html += '</a>';
        }
        html += ': '+result;
        if (job['voting'] == false) {
            html += ' (non-voting)';
        }
        html += '</span>';
    });

    html += '</div></div>';
    return html;
}

function update_timeout() {
    if (!window.zuul_enable_status_updates) {
        setTimeout(update_timeout, 5000);
        return;
    }

    window.zuul_graph_update_count += 1;

    update();
    /* Only update graphs every minute */
    if (window.zuul_graph_update_count > 11) {
        window.zuul_graph_update_count = 0;
        update_graphs();
    }

    setTimeout(update_timeout, 5000);
}

function update() {
    var html = '';

    $.getJSON('http://zuul.openstack.org/status.json', function(data) {
        if ('message' in data) {
            $("#message-container").attr('class', 'topMessage');
            $("#message").html(data['message']);
        } else {
            $("#message-container").removeClass('topMessage');
            $("#message").html('');
        }

        html += '<br style="clear:both"/>';

        $.each(data['pipelines'], function(i, pipeline) {
            html = html + format_pipeline(pipeline);
        });

        html += '<br style="clear:both"/>';
        $("#pipeline-container").html(html);
    });
}

function update_graphs() {
    $('.graph').each(function(i, img) {
        var newimg = new Image()
        var parts = img.src.split('#');
        newimg.src = parts[0] + '#' + new Date().getTime();
        $(newimg).load(function (x) {
            img.src = newimg.src;
        });
    });
}

$(function() {
    window.zuul_graph_update_count = 0;
    update_timeout();

    $(document).on({
        'show.visibility': function() {
            window.zuul_enable_status_updates = true;
            update();
            update_graphs();
        },
        'hide.visibility': function() {
            window.zuul_enable_status_updates = false;
        }
    });

});
