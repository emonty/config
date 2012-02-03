class jenkins_master {

  file { '/etc/apt/sources.list.d/jenkins':
    owner => 'root',
    group => 'root',
    mode => 444,
    ensure => 'present',
    content => "deb http://pkg.jenkins-ci.org/debian binary/",
    replace => 'true',
  }

  file { '/etc/apache2/sites-available/jenkins':
    owner => 'root',
    group => 'root',
    mode => 444,
    ensure => 'present',
    source => "puppet:///modules/jenkins_master/apache.conf",
    replace => 'true',
    require => Package['apache2'],
  }

  file { '/etc/apache2/sites-enabled/apache2':
    target => '/etc/apache2/site-available/jenkins',
    ensure => link,
    require => File['/etc/apache2/sites-available/jenkins'],
  }

  $packages = [
    jenkins,
    apache2
  ]

  package { $packages:
    ensure => "latest",
    require => File['/etc/apt/sources.list.d/jenkins'],
  }

  exec { "update apt cache":
    subscribe => [ File["/etc/apt/sources.list.d/jenkins"]],
    refreshonly => true,
    path => "/bin:/usr/bin",
    command => "apt-get update",
  }

  exec { "gracefully restart apache":
    subscribe => [ File["/etc/apache2/sites-available/jenkins"]],
    refreshonly => true,
    path => "/bin:/usr/bin:/usr/sbin",
    command => "apache2ctl graceful",
  }

}