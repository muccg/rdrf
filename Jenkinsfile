#!groovy

node {
    stage 'Checkout'
        checkout scm

        // 'fix' detached HEAD.
        sh "git checkout -f ${env.BRANCH_NAME}"
        sh "git pull -f"

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
