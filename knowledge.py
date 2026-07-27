KNOWLEDGE_BASE = [
    "CrashLoopBackOff: container starts then exits repeatedly. Usually caused by an application error on startup. Fix: check 'kubectl logs <pod>' for the exit reason, common causes are missing environment variables or a failed dependency connection.",
    
    "ImagePullBackOff: Kubernetes cannot pull the specified container image. Common causes: wrong image tag, typo in image name, or missing registry credentials. Fix: verify the image name/tag exists with 'docker pull <image>' manually, and check imagePullSecrets if using a private registry.",
    
    "OOMKilled: container exceeded its memory limit and was killed. Fix: increase resources.limits.memory in the deployment YAML, or investigate the application for a memory leak if usage keeps growing over time.",
    
    "Pending pod status: pod cannot be scheduled onto any node. Common causes: insufficient CPU/memory on all nodes, or a nodeSelector/affinity rule that no node satisfies. Fix: check 'kubectl describe pod' Events section for the exact scheduling failure reason.",
    
    "Jenkins build failing with dependency resolution error: usually means a package version in package.json/requirements.txt is no longer available in the registry. Fix: check the registry directly, or pin to a known-available version.",

    "Docker container exits immediately with no logs: often means the container's main process finished or crashed instantly, common with misconfigured CMD/ENTRYPOINT. Fix: run the image interactively with 'docker run -it <image> /bin/sh' to debug manually.",
]