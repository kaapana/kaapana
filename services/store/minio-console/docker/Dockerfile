FROM node:17 as uilayer

LABEL IMAGE=minio-console
LABEL VERSION=0.15.6

WORKDIR /gitcode

RUN  \
     git clone https://github.com/minio/console.git && cd console && \
     git checkout b658301725a2cfdf3fb8cdd0e248c5f9f6590074

COPY files/provider.go /gitcode/console/pkg/auth/idp/oauth2/provider.go 
COPY files/LoginPage.tsx /gitcode/console/portal-ui/src/screens/LoginPage/LoginPage.tsx
COPY files/utils.ts /gitcode/console/portal-ui/src/screens/Console/Buckets/ListBuckets/Objects/utils.ts

WORKDIR /app
# COPY ./portal-ui/package.json ./
RUN cp  /gitcode/console/portal-ui/package.json ./
# COPY ./portal-ui/yarn.lock ./
RUN cp  /gitcode/console/portal-ui/yarn.lock ./
RUN yarn install

# COPY ./portal-ui .
RUN cp -r  /gitcode/console/portal-ui/* .

RUN make build-static

USER node

FROM golang:1.17 as golayer

RUN apt-get update -y && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ADD go.mod /go/src/github.com/minio/console/go.mod
COPY --from=uilayer /gitcode/console/go.mod /go/src/github.com/minio/console/go.mod
# ADD go.sum /go/src/github.com/minio/console/go.sum
COPY --from=uilayer /gitcode/console/go.sum /go/src/github.com/minio/console/go.sum
WORKDIR /go/src/github.com/minio/console/

# Get dependencies - will also be cached if we won't change mod/sum
RUN go mod download

COPY --from=uilayer /gitcode/console/ /go/src/github.com/minio/console/
WORKDIR /go/src/github.com/minio/console/

ENV CGO_ENABLED=0

COPY --from=uilayer /app/build /go/src/github.com/minio/console/portal-ui/build
RUN go build --tags=kqueue,operator -ldflags "-w -s" -a -o console ./cmd/console

FROM registry.access.redhat.com/ubi8/ubi-minimal:8.5
EXPOSE 9090

COPY --from=golayer /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=golayer /go/src/github.com/minio/console/console .

ENTRYPOINT ["/console"]