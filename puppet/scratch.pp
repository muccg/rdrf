#
node default {
  include ccgcommon
  include ccgcommon::source
  include ccgapache
  include python
  include repo::epel
  include repo::ius
  include repo::pgrpms
  include globals
  $release = '0.7.5-1'

  $user = $globals::aws_user

  
  class {'s3cmd':
    aws_access_key => $globals::aws_s3backup_access_key,
    aws_secret_key => $globals::aws_s3backup_secret_key,
    gpg_passphrase => 'This is our secret passphrase',
    owner => $user
  }

  class {'ccgscript::mongodb_backup':
    dumpdir => "/home/$user/dump/",
    s3dir   => "s3://$globals::aws_backup_bucket/$globals::aws_backup_bucket_1day/rdrf-scratch/"
  }

  # cronjob to run mongo-backup
  cron { "mongo-backup":
     ensure  => present,
     command => $ccgscript::mongodb_backup::script,
     user    => $user,
     minute  => [ 0 ],
     hour  => [ 7 ],
  }

  $dbdriver = 'django.db.backends.postgresql_psycopg2'
  $dbhost = $globals::dbhost_syd_scratch
  $dbuser = $globals::dbuser_syd_scratch
  $dbpass = $globals::dbpass_syd_scratch
  $dbname = 'rdrf_scratch'

  class { 'monit::packages':
    packages => ['rsyslog', 'sshd', 'denyhosts', 'httpd'],
  }

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
  
  $django_config = {
    deployment          => 'prod',
    release             => '0.7.5-1',
    dbdriver            => 'django.db.backends.postgresql_psycopg2',
    dbuser              =>  $globals::dbuser_syd_scratch,
    dbpass              =>  $globals::dbpass_syd_scratch,
    dbname              =>  'rdrf_scratch',
    memcache            =>  $globals::memcache_syd,
    secretkey           =>  $globals::secretkey_rdrf_scratch,
    admin_email         =>  $global::system_email,
    custom_installroot  => '/usr/local/webapps/rdrf/lib/python2.7/site-packages',
  }
  
  package {'rdrf': ensure => $release, provider => 'yum_nogpgcheck'} ->
  django::config { 'rdrf':
    config_hash => $django_config,
  } ->
  django::syncdbmigrate{'rdrf':
    dbsync  => true,
    require => [
      Package[$packages],
      Ccgdatabase::Postgresql[$django_config['dbname']],
      Package['rdrf'],
      Django::Config['rdrf'] ]
  }
}
