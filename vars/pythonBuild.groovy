def call() {
    sh 'pip install flake8 bandit'
    sh 'flake8 scanner/ notifier/ db/'
    sh 'bandit -r scanner/ notifier/ -ll'
    sh 'pip install -r requirements.txt'
    sh 'pytest tests/ --cov=scanner --cov=notifier --cov-report=xml --cov-fail-under=85'
}
