<#-- Kaapana override of base/login/login-otp.ftl (KC 26.4.6):
     Material floating-label OTP field, matching login.ftl. The (rare) multi-
     credential chooser keeps the inherited markup. -->
<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('totp'); section>
    <#if section="header">
        ${msg("doLogIn")}
    <#elseif section="form">
        <form id="kc-otp-login-form" class="${properties.kcFormClass!}" onsubmit="login.disabled = true; return true;" action="${url.loginAction}" method="post">
            <#if otpLogin.userOtpCredentials?size gt 1>
                <div class="${properties.kcFormGroupClass!}">
                    <#list otpLogin.userOtpCredentials as otpCredential>
                        <input id="kc-otp-credential-${otpCredential?index}" class="${properties.kcLoginOTPListInputClass!}" type="radio" name="selectedCredentialId" value="${otpCredential.id}" <#if otpCredential.id == otpLogin.selectedCredentialId>checked="checked"</#if>>
                        <label for="kc-otp-credential-${otpCredential?index}" class="${properties.kcLoginOTPListClass!}" tabindex="${otpCredential?index}">
                            <span class="${properties.kcLoginOTPListItemHeaderClass!}">
                                <span class="${properties.kcLoginOTPListItemIconBodyClass!}"><i class="${properties.kcLoginOTPListItemIconClass!}" aria-hidden="true"></i></span>
                                <span class="${properties.kcLoginOTPListItemTitleClass!}">${otpCredential.userLabel}</span>
                            </span>
                        </label>
                    </#list>
                </div>
            </#if>

            <div class="${properties.kcFormGroupClass!}">
                <input id="otp" name="otp" autocomplete="one-time-code" type="text" class="${properties.kcInputClass!}" placeholder=" "
                       autofocus <#if messagesPerField.existsError('totp')>aria-invalid="true"</#if> dir="ltr"/>
                <label for="otp">${msg("loginOtpOneTime")}</label>
                <#if messagesPerField.existsError('totp')>
                    <span id="input-error-otp-code" class="${properties.kcInputErrorMessageClass!}" aria-live="polite">
                        ${kcSanitize(messagesPerField.get('totp'))?no_esc}
                    </span>
                </#if>
            </div>

            <div id="kc-form-buttons" class="${properties.kcFormButtonsClass!}">
                <input class="${properties.kcButtonClass!} ${properties.kcButtonPrimaryClass!} ${properties.kcButtonBlockClass!} ${properties.kcButtonLargeClass!}" name="login" id="kc-login" type="submit" value="${msg("doLogIn")}" />
            </div>
        </form>
    </#if>
</@layout.registrationLayout>
