#!groovy

node {
    env.DOCKER_USE_HUB = 1
    def deployable_branches = ["master", "next_release"]

    stage('Checkout') {
        checkout scm
    }

    stage('Dev build') {
        echo "Branch is: ${env.BRANCH_NAME}"
        echo "Build is: ${env.BUILD_NUMBER}"
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh docker_warm_cache'
            sh './develop.sh dev_build'
            sh './develop.sh check_migrations'
        }
    }

    stage('Unit tests') {
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh runtests'
        }
        step([$class: 'JUnitResultArchiver', testResults: '**/data/tests/*.xml'])
    }

    stage('Dev aloe tests') {
        wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
            sh './develop.sh dev_aloe'
        }
        step([$class: 'ArtifactArchiver', artifacts: '**/data/selenium/dev/scratch/*.png', fingerprint: false, excludes: null])
        step([$class: 'ArtifactArchiver', artifacts: '**/data/selenium/dev/log/*.log', fingerprint: false, excludes: null])
        step([$class: 'JUnitResultArchiver', testResults: '**/data/selenium/dev/scratch/*.xml'])
    }

    if (deployable_branches.contains(env.BRANCH_NAME)) {

        stage('Prod build') {
            wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
                sh './develop.sh prod_build'
            }
        }

        stage('Prod aloe tests') {
            wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
                sh './develop.sh prod_aloe'
                step([$class: 'ArtifactArchiver', artifacts: '**/data/selenium/prod/scratch/*.png', fingerprint: false, excludes: null])
                step([$class: 'ArtifactArchiver', artifacts: '**/data/selenium/prod/log/*.log', fingerprint: false, excludes: null])
                step([$class: 'JUnitResultArchiver', testResults: '**/data/selenium/prod/scratch/*.xml'])
            }
        }

        stage('Publish docker image') {
            withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'dockerbot',
                              usernameVariable: 'DOCKER_USERNAME',
                              passwordVariable: 'DOCKER_PASSWORD']]) {
                wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'XTerm']) {
                    sh './develop.sh ci_docker_login'
                    sh './develop.sh publish_docker_image'
                }
            }
        }
    }
}
