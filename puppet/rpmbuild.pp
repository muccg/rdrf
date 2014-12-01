# A centos instance for building RPM packages
node default {
  $custom_hostname = 'aws-rpmbuild-centos6.ec2.ccgapps.com.au'
  include role::rpmbuild::sydney
}
