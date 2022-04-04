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

or copy that part:

spec:
  replicas: 1
  selector:
    matchLabels:
      app-name: landingpage
  template:
    metadata:
      creationTimestamp: null
      labels:
        app-name: landingpage
    spec:
      volumes:
        - name: common-data-file
          configMap:
            name: landing-page-config
            defaultMode: 420
        - name: landing-dev-files
          hostPath:
            path: /home/ubuntu/dev/base-landing-page/files/kaapana_app/src
            type: DirectoryOrCreate
      containers:
        - name: landingpage
          image: >-
            {{  .Values.global.registry_url }}/landing-page-kaapana:0.1.3-dev
          command:
            - sh
          args:
            - dev.sh
          ports:
            - name: landing-http
              containerPort: 5000
              protocol: TCP
          resources:
            limits:
              memory: 10Gi
            requests:
              memory: 10Gi
          volumeMounts:
            - name: common-data-file
              mountPath: /app/jsons
            - name: landing-dev-files
              mountPath: /landing/app/src
          livenessProbe:
            httpGet:
              path: /
              port: landing-http
              scheme: HTTP
            initialDelaySeconds: 10
            timeoutSeconds: 1
            periodSeconds: 20
            successThreshold: 1
            failureThreshold: 3
          terminationMessagePath: /dev/termination-log
          terminationMessagePolicy: File
          imagePullPolicy: Always
      restartPolicy: Always
      terminationGracePeriodSeconds: 30
      dnsPolicy: ClusterFirst
      securityContext: {}
      imagePullSecrets:
        - name: registry-secret