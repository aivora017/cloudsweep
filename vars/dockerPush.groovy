def call(String image, String tag) {
    withCredentials([usernamePassword(credentialsId: 'ghcr-token',
                                      usernameVariable: 'GHCR_USER',
                                      passwordVariable: 'GHCR_PASS')]) {
        sh "echo \$GHCR_PASS | docker login ghcr.io -u \$GHCR_USER --password-stdin"
        sh """docker buildx build \\
            --cache-from ${image}:latest \\
            --cache-to type=inline \\
            -t ${image}:${tag} \\
            -t ${image}:latest \\
            --push ."""
    }
}
