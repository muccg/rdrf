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

    stage 'Lettuce tests'
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh lettuce'
        }
        step([$class: 'JUnitResultArchiver', testResults: '**/data/selenium/*.xml'])
        step([$class: 'ArtifactArchiver', artifacts: '**/data/selenium/*.png'])

    stage 'Docker prod build'
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh prod_build'
        }

    stage 'Publish docker image'
        withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'dockerbot',
                          usernameVariable: 'DOCKER_USERNAME',
                          passwordVariable: 'DOCKER_PASSWORD']]) {
            wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
                sh './develop.sh ci_docker_login'
                sh './develop.sh publish_docker_image'
            }
        }

}
