FROM registry.hzdr.de/kaapana/public/collabora-code-patched:23.05.5.4.1

# Fix CVEs in base debian packages
#   - krb5 (krb5-locales + libs):  CVE-2024-37371
#   - libexpat1:                   CVE-2024-45491, CVE-2024-45492
#   - libgnutls30:                 CVE-2026-33845, CVE-2026-42010
#   - openssl / libssl3:           CVE-2026-31789
# Three workarounds needed:
#   1. The image's apt sources track "stable", which now points to a newer Debian release
#      than the image is built on — rewrite them to "bookworm" so apt doesn't cross-grade.
#   2. Upstream removed the 23.05 CODE-deb repo (404) so drop its apt source, every upgraded package comes from Debian anyway
#   3. Upgrade only the listed packages: a full `apt-get upgrade` fails on libc6
USER root
RUN sed -i 's/\bstable\b/bookworm/g' /etc/apt/sources.list.d/debian.sources && \
    grep -l 'collaboraoffice.com' /etc/apt/sources.list.d/* | xargs -r rm -f && \
    apt-get update && \
    apt-get install -y --only-upgrade \
        krb5-locales libkrb5-3 libkrb5support0 libk5crypto3 libgssapi-krb5-2 \
        libexpat1 \
        libgnutls30 \
        libssl3 openssl && \
    rm -rf /var/lib/apt/lists/*
USER 100

LABEL IMAGE="collabora"
LABEL VERSION="23.05.5.4.1"
LABEL BUILD_IGNORE="False"
