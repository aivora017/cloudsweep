def call(String release, String chart, String namespace) {
    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
        sh """helm upgrade --install ${release} ${chart} \\
            --namespace ${namespace} \\
            --create-namespace \\
            --atomic \\
            --timeout 5m"""
    }
}
