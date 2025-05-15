# UI Tests

## Setting things up
- `cd ./tests/ui && npm install`
- set `KAAPANA_TEST_INSTANCE_UI` to your instance e.g. `export KAAPANA_TEST_INSTANCE_UI=https://localhost`


## Run tests
- Run tests *headless* with `npx playwright test` show the results using `npx playwright show-report`
- Run tests in UI mode using `npx playwright test --ui`

## Create tests
- Have a look at the [playwright documentation](https://playwright.dev/docs/writing-tests) to get the basics
- Record Tests CLI `npx playwright codegen` ([documentation](https://playwright.dev/docs/codegen-intro#recording-a-test))
    1. run `npx playwright codegen $KAAPANA_TEST_INSTANCE_UI`
    2. Record your test
    3. Stop the recording by pressing the red recording button
    4. Create a new file in the `test` dir and past the generated code (if the tastcase fits to other test cases in one file it can be added there)
    5. Set a proper title (e.g. the first argument of the test function)
- Record Tests VS Code ([documentation](https://playwright.dev/docs/getting-started-vscode))
    1. Install `Playwright Test for VSCode` Extension in VSCode
    2. In the testing sidebar (beaker on the sidebar left) A playwright menue should apear
    3. Select `Record new` a browser will open to record the test and a new file is automatically created
- Make sure that the first goto goes to `/` (e.g. the base url from the configuration) so that the base url (e.g. `KAAPANA_TEST_INSTANCE_UI` is picked up.)