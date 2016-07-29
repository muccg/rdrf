#!groovy

node {
    env.DOCKER_USE_HUB = 1

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
        step([$class: 'JUnitResultArchiver', testResults: '**/data/tests/*.xml'])

    stage 'Selenium tests'
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh selenium'
        }
        step([$class: 'JUnitResultArchiver', testResults: '**/data/selenium/*.xml'])

    stage 'Lettuce tests'
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh lettuce'
        }
        step([$class: 'JUnitResultArchiver', testResults: '**/data/selenium/*.xml'])
        step([$class: 'ArtifactArchiver', artifacts: '**/data/selenium.*.png'])
}
