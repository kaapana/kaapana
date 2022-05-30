function Controller() {
  gui.pageWidgetByObjectName("WelcomePage").completeChanged.connect(function() {
    gui.clickButton(buttons.NextButton);
  });

  installer.installationFinished.connect(function() {
    gui.clickButton(buttons.CommitButton);
  });
}

Controller.prototype.WelcomePageCallback = function() {
}

Controller.prototype.CredentialsPageCallback = function() {
  var loginWidget = gui.currentPageWidget().loginWidget;

  loginWidget.EmailLineEdit.text = "h.gao@dkfz-heidelberg.de";
  loginWidget.PasswordLineEdit.text = "jBAtabJNx6samRhYBtjZuf2DXWKm5LDu";

  gui.clickButton(buttons.NextButton);
}

Controller.prototype.ObligationsPageCallback = function()
{
  var obligationsPage = gui.currentPageWidget();
  var companyNameLineEdit = gui.findChild(obligationsPage, "CompanyName");

  obligationsPage.obligationsAgreement.setChecked(true);

  if (null != companyNameLineEdit) {
    companyNameLineEdit.text = "German Cancer Research Center (DKFZ)";
  }

  obligationsPage.completeChanged();

  gui.clickButton(buttons.NextButton);
}

Controller.prototype.IntroductionPageCallback = function() {
  gui.clickButton(buttons.NextButton);
}

Controller.prototype.DynamicTelemetryPluginFormCallback = function() {
  var disableStatisticRadioButton = gui.findChild(gui.currentPageWidget(), "disableStatisticRadioButton");

  if (null != disableStatisticRadioButton) {
    disableStatisticRadioButton.checked = true;
  }

  gui.clickButton(buttons.NextButton);
}

Controller.prototype.TargetDirectoryPageCallback = function() {
  gui.currentPageWidget().TargetDirectoryLineEdit.text = "/Qt";
  gui.clickButton(buttons.NextButton);
}

Controller.prototype.ComponentSelectionPageCallback = function() {
  var componentSelectionPage = gui.currentPageWidget();
  var archiveCheckBox = gui.findChild(componentSelectionPage, "Archive");
  var fetchCategoryButton = gui.findChild(componentSelectionPage, "FetchCategoryButton");

  if (null != archiveCheckBox && null != fetchCategoryButton) {
    archiveCheckBox.checked = true;
    fetchCategoryButton.click();
  }

  componentSelectionPage.deselectAll();
  componentSelectionPage.selectComponent("qt.qt5.5129.gcc_64");
  componentSelectionPage.selectComponent("qt.qt5.5129.qtscript");
  componentSelectionPage.selectComponent("qt.qt5.5129.qtwebengine");

  gui.clickButton(buttons.NextButton);
}

Controller.prototype.LicenseAgreementPageCallback = function() {
  gui.currentPageWidget().AcceptLicenseRadioButton.checked = true;
  gui.clickButton(buttons.NextButton);
}

Controller.prototype.StartMenuDirectoryPageCallback = function() {
  gui.clickButton(buttons.NextButton);
}

Controller.prototype.ReadyForInstallationPageCallback = function() {
  gui.clickButton(buttons.CommitButton);
}

Controller.prototype.PerformInstallationPageCallback = function() {
}

Controller.prototype.FinishedPageCallback = function() {
  var runItCheckBox = gui.findChild(gui.currentPageWidget(), "launchQtCreatorCheckBox");

  if (null != runItCheckBox) {
    runItCheckBox.checked = false;
  }

  gui.clickButton(buttons.FinishButton);
}
