#
node default {
  $custom_hostname = 'aws-syd-rdrf-staging.ec2.ccgapps.com.au'

  include ccgcommon
  include ccgcommon::source
  include ccgapache
  include python
  include repo::sydney
  include repo::upgrade
  include repo::repo::ius
  include repo::repo::ccgtesting
  include repo::repo::ccgdeps
  class { 'yum::repo::pgdg93':
    stage => 'setup',
  }
  include globals
  include ccgdatabase::postgresql::devel

  # server
  class { 'mongodb': 
    smallfiles => true,
    journal  => false,
  }

  # client
  package { 'mongodb':
    ensure => installed
  }

  $packages = ['python27-psycopg2']
  package {$packages: ensure => installed}

  # tests need firefox and a virtual X server
  $testingpackages = ['firefox', 'xorg-x11-server-Xvfb', 'dbus-x11']
  package {$testingpackages:
    ensure => installed,
  }

  # There are some leaked local secrets here we don't care about
  $django_config = {
    deployment         => 'staging',
    dbdriver           => 'django.db.backends.postgresql_psycopg2',
    dbhost             => '',
    dbname             => 'rdrf_staging',
    dbuser             => 'rdrf',
    dbpass             => 'rdrf',
    memcache           => $globals::memcache_syd,
    secret_key         => '*&^*&768768YFYTFYHGGHCgcgfcg',
    allowed_hosts      => 'localhost .ccgapps.com.au',
    csrf_cookie_domain => '.ccgapps.com.au',
    key_prefix         => 'rdrf_staging_'
  }

  # postgressql database
  ccgdatabase::postgresql::db { $django_config['dbname']: user => $django_config['dbuser'], password => $django_config['dbpass'] }

  package {'rdrf': ensure => installed,
    provider => 'yum_nogpgcheck',
    require => Package[$packages]
  }

  django::config { 'rdrf':
    config_hash => $django_config,
    require => Package['rdrf']
  }

  django::syncdbmigrate{'rdrf':
    dbsync  => true,
    require => [
      Ccgdatabase::Postgresql::Db[$django_config['dbname']],
      Package['rdrf'],
      Django::Config['rdrf'] ]
  }

}
