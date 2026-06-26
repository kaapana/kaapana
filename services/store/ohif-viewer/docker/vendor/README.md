Vendored frontend sources used by the OHIF viewer image.

- `ohif-ai-viewers/` contains `Viewers/` from `CCI-Bonn/OHIF-AI`.
- Upstream commit: `dc17dcfa7f9ffd1416e3a03ad6bb5b70c3101a8c`.
- License: MIT, see `ohif-ai-viewers/LICENSE`.
- The Docker build applies `../files/customization.patch` on top of this source tree.

Keeping this source in-repo makes the OHIF image build independent of GitHub
availability and protects us from upstream changes.

Do not remove the vendored `LICENSE` files. The Docker build copies them into
the final image at `/usr/share/nginx/html/ohif/vendor-licenses/` so redistributed
images include the required copyright and permission notices.
