#!groovy

node {
    stage 'Checkout'
        checkout scm

    stage 'Docker dev build'
        echo "Branch is: ${env.BRANCH_NAME}"
        echo "Build is: ${env.BUILD_NUMBER}"
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh dev_build'
        }

    stage 'Unit tests'
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh runtests'
        }

    stage 'Selenium tests'
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh selenium'
        }

    stage 'Lettuce tests'
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh lettuce'
        }
}
