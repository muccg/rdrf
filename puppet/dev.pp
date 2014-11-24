#
node default {
  include ccgcommon
  include ccgcommon::source
  include ccgapache
  include python
  include repo
  include repo::repo::ius
  include repo::repo::ccgdeps
  class { 'yum::repo::pgdg93':
    stage => 'setup',
  }
  include globals
  include ccgdatabase::postgresql::devel
  include ccgdatabase::mysql::devel

  $user = 'ccg-user' # $globals::aws_user for production

  class {'s3cmd':
    aws_access_key => $globals::aws_s3backup_access_key,
    aws_secret_key => $globals::aws_s3backup_secret_key,
    gpg_passphrase => 'This is our secret passphrase',
    owner => $user 
  }

  #class {'ccgscript::mongodb_backup':
  #  dumpdir => '/home/ccg-user/dump/',
  #  s3dir   => "s3://$globals::aws_backup_bucket/$globals::aws_backup_bucket_1day/rdrf-dev/"
  #}

  # cronjob to run mongo-backup
  #cron { "mongo-backup":
  #   ensure  => present,
  #   command => $ccgscript::mongodb_backup::script,
  #   user    => $user,
  #   minute  => [ 0 ],
  #   hour  => [ 7 ],
  #}

  # MongoDB server
  class { 'mongodb': 
    smallfiles => true,
    journal  => false,
  }

  # client
  package { 'mongodb':
    ensure => installed
  }


  # tests need firefox and a virtual X server
  $testingpackages = ['firefox', 'xorg-x11-server-Xvfb', 'dbus-x11']
  package {$testingpackages:
    ensure => installed,
  }
  
  # postgressql databases
  ccgdatabase::postgresql::db { 'rdrf': user => 'rdrf', password => 'rdrf' }


}
