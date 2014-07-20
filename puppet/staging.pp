#
node default {
  include ccgcommon
  include ccgcommon::source
  include ccgapache
  include python
  include repo::epel
  include repo::ius
  include repo::pgrpms
  include repo::ccgtesting
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
    deployment  => 'staging',
    dbdriver    => 'django.db.backends.postgresql_psycopg2',
    dbhost      => '',
    dbname      => 'rdrf_staging',
    dbuser      => 'rdrf',
    dbpass      => 'rdrf',
    allowed_hosts => 'localhost ccgapps.com.au',
    memcache    => $globals::memcache_syd,
    secret_key  => '*&^*&768768YFYTFYHGGHCgcgfcg',
    custom_installroot => '/usr/local/webapps/rdrf/lib/python2.7/site-packages',

  }

  # postgressql database
  ccgdatabase::postgresql::db { $django_config['dbname']: user => $django_config['dbuser'], password => $django_config['dbpass'] }

  package {'rdrf': ensure => installed,
      provider => 'yum_nogpgcheck',
  require => Package[$packages] } ->

  django::config { 'rdrf':
    config_hash => $django_config,
    require => Package['rdrf']
  } ->

  django::syncdbmigrate{'rdrf':
    dbsync  => true,
    require => Ccgdatabase::Postgresql::Db[$django_config['dbname']]
  }

}
