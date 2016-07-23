#!groovy

node {
    stage 'Debug'
        sh 'env'

    stage 'Checkout'
        checkout scm

    stage 'Docker dev build'
        echo "Branch is: ${env.BRANCH_NAME}"
        echo "Build is: ${env.BUILD_NUMBER}"
        sh './develop.sh dev_build'

    stage 'Unit tests'
        sh './develop.sh runtests'

    stage 'Selenium tests'
        sh './develop.sh selenium'

    stage 'Lettuce tests'
        sh './develop.sh lettuce'
}
