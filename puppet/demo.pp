#
node default {
  $custom_hostname = 'aws-syd-rdrf-demo.ec2.ccgapps.com.au'

  include ccgcommon
  include ccgcommon::source
  include ccgapache
  include python
  include repo::sydney
  include repo::upgrade
  include repo::repo::ius
  include repo::repo::ccgcentos
  include repo::repo::ccgdeps
  class { 'yum::repo::pgdg93':
    stage => 'setup',
  }
  include globals

  $user = $globals::aws_user
  
  class {'s3cmd':
    aws_access_key => $globals::aws_s3backup_access_key,
    aws_secret_key => $globals::aws_s3backup_secret_key,
    gpg_passphrase => 'This is our secret passphrase',
    owner => $user
  }

  class {'ccgscript::mongodb_backup':
    dumpdir => "/home/$user/dump/",
    s3dir   => "s3://$globals::aws_backup_bucket/$globals::aws_backup_bucket_1day/rdrf-demo/"
  }

  # cronjob to run mongo-backup
  cron { "mongo-backup":
     ensure  => present,
     command => $ccgscript::mongodb_backup::script,
     user    => $user,
     minute  => [ 0 ],
     hour  => [ 7 ],
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
    release             => '0.8.3-1',
    dbdriver            => 'django.db.backends.postgresql_psycopg2',
    dbserver            => $globals::dbhost_rds_syd_postgresql_prod,
    dbuser              => $globals::dbuser_syd_prod,
    dbpass              => $globals::dbpass_syd_prod,
    dbname              => 'rdrf_demo',
    memcache            => $globals::memcache_syd,
    secretkey           => $globals::secretkey_rdrf_demo,
    admin_email         => $globals::system_email,
    allowed_hosts       => 'localhost .ccgapps.com.au',
    csrf_cookie_domain  => '.ccgapps.com.au',
    key_prefix          => 'rdrf_demo_'
  }
  
  package {'rdrf':
    ensure => $django_config['release'],
    provider => 'yum_nogpgcheck',
    require => Package[$packages]
  }

  django::config { 'rdrf':
    config_hash => $django_config,
    require => Package['rdrf']
  }

  django::syncdbmigrate { 'rdrf':
    dbsync  => true,
    require => [
      Package['rdrf'],
      Django::Config['rdrf'] ]
  }
}
