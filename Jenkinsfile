@Library('cloudsweep') _

pipeline {
    agent any

    environment {
        IMAGE = 'ghcr.io/aivora017/cloudsweep'
        TAG   = "${env.GIT_COMMIT.take(7)}"
    }

    stages {
        stage('Lint') {
            steps {
                sh 'pip install flake8 bandit'
                sh 'flake8 scanner/ notifier/ db/'
                sh 'bandit -r scanner/ notifier/ -ll'
            }
        }

        stage('Test') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pytest tests/ --cov=scanner --cov=notifier --cov-report=xml --cov-fail-under=85'
            }
        }

        stage('Build and Push') {
            when { branch 'main' }
            steps {
                script {
                    dockerPush(env.IMAGE, env.TAG)
                }
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps {
                script {
                    helmDeploy('cloudsweep', './helm/cloudsweep', 'cloudsweep')
                }
            }
        }
    }

    post {
        success {
            script {
                if (env.BRANCH_NAME == 'main') {
                    withCredentials([string(credentialsId: 'db-url', variable: 'DATABASE_URL')]) {
                        sh '''kubectl run smoke-test --image=postgres:15-alpine \
                            --rm -i --restart=Never -n cloudsweep \
                            -- psql $DATABASE_URL -c "SELECT count(*) FROM findings;"'''
                    }
                }
            }
        }
        failure {
            slackSend(channel: '#alerts', message: "Build failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}")
        }
    }
}
