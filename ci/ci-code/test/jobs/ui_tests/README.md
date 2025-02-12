## Test execution
### Via docker-compose
```
docker-compose up --exit-code-from tests
docker-compose up --exit-code-from tests --build ### if you want to rebuild the image
```
This starts a `selenium-standalone/chrome` container.
The tests are executed headless.