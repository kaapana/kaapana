For development with landing page adjust in the respective sections as well take a look at the Dockerfile

---
        # containers
        imagePullPolicy: Always
        command: ["sh"]
        args: ["dev.sh"] 
          # resources
          requests:
            memory: 10Gi
          limits:
            memory: 10Gi
          # volumeMounts
          - name: landing-dev-files
            mountPath: /landing/app/src
      # volumes
      - name: landing-dev-files
        hostPath:
          path: /home/ubuntu/dev/base-landing-page/files/kaapana_app/src
          type: DirectoryOrCreate
