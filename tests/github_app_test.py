"""Tests for GitHub App Installation access token extraction plugin."""

from typing import TypedDict

import pytest
from pytest_mock import MockerFixture

from github.Auth import AppAuth, AppInstallationAuth

from awx_plugins.credentials import github_app as gh_app_plugin_mod


class AppInstallIds(TypedDict):
    """Schema for augmented extractor function keyword args."""

    app_id: str
    install_id: str


@pytest.mark.parametrize(
    ('extract_github_app_install_token_args', 'expected_error_msg'),
    (
        pytest.param(
            {
                'app_id': 'invalid',
                'install_id': '666',
            },
            '^Expected GitHub App or Client ID to be an integer or a string '
            r'starting with `Iv1\.` followed by 16 hexadecimal digits, but got'
            " 'invalid'$",
            id='gh-app-id-broken-text',
        ),
        pytest.param(
            {
                'app_id': 'Iv1.bbbbbbbbbbbbbbb',
                'install_id': '666',
            },
            '^Expected GitHub App or Client ID to be an integer or a string '
            r'starting with `Iv1\.` followed by 16 hexadecimal digits, but got'
            " 'Iv1.bbbbbbbbbbbbbbb'$",
            id='gh-app-id-client-id-not-enough-chars',
        ),
        pytest.param(
            {
                'app_id': 'Iv1.bbbbbbbbbbbbbbbx',
                'install_id': '666',
            },
            '^Expected GitHub App or Client ID to be an integer or a string '
            r'starting with `Iv1\.` followed by 16 hexadecimal digits, but got'
            " 'Iv1.bbbbbbbbbbbbbbbx'$",
            id='gh-app-id-client-id-broken-hex',
        ),
        pytest.param(
            {
                'app_id': 'Iv1.bbbbbbbbbbbbbbbbb',
                'install_id': '666',
            },
            '^Expected GitHub App or Client ID to be an integer or a string '
            r'starting with `Iv1\.` followed by 16 hexadecimal digits, but got'
            " 'Iv1.bbbbbbbbbbbbbbbbb'$",
            id='gh-app-id-client-id-too-many-chars',
        ),
        pytest.param(
            {
                'app_id': 999,
                'install_id': 'invalid',
            },
            '^Expected GitHub App Installation ID to be an integer '
            "but got 'invalid'$",
            id='gh-app-invalid-install-id-with-int-app-id',
        ),
        pytest.param(
            {
                'app_id': '999',
                'install_id': 'invalid',
            },
            '^Expected GitHub App Installation ID to be an integer '
            "but got 'invalid'$",
            id='gh-app-invalid-install-id-with-str-digit-app-id',
        ),
        pytest.param(
            {
                'app_id': 'Iv1.cccccccccccccccc',
                'install_id': 'invalid',
            },
            '^Expected GitHub App Installation ID to be an integer '
            "but got 'invalid'$",
            id='gh-app-invalid-install-id-with-client-id',
        ),
    ),
)
def test_github_app_invalid_args(
    extract_github_app_install_token_args: AppInstallIds,
    expected_error_msg: str,
) -> None:
    """Test that invalid arguments make token extractor bail early."""
    with pytest.raises(ValueError, match=expected_error_msg):
        gh_app_plugin_mod.extract_github_app_install_token(
            github_api_url='https://github.com',
            private_rsa_key='key',
            **extract_github_app_install_token_args,
        )


class _FakeAppInstallationAuth(AppInstallationAuth):
    @property
    def token(self: '_FakeAppInstallationAuth') -> str:
        return 'token-sentinel'


def test_github_app_github_authentication(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test successful GitHub authentication."""
    monkeypatch.setattr(
        gh_app_plugin_mod.Auth,
        'AppInstallationAuth',
        _FakeAppInstallationAuth,
    )

    get_installation_auth_spy = mocker.spy(
        gh_app_plugin_mod.Auth,
        'AppInstallationAuth',
    )
    github_initializer_spy = mocker.spy(gh_app_plugin_mod, 'Github')

    token = gh_app_plugin_mod.extract_github_app_install_token(
        github_api_url='https://github.com',
        app_id='123',
        install_id='456',
        private_rsa_key='example-key',
    )

    assert token == 'token-sentinel'

    get_installation_auth_spy.assert_called_once_with(
        mocker.ANY,
        456,  # noqa: WPS432
        None,
        None,
    )
    first_arg_to_get_installation_auth = (
        get_installation_auth_spy.
        call_args[0][0]
    )
    assert isinstance(first_arg_to_get_installation_auth, AppAuth)
    assert first_arg_to_get_installation_auth.app_id == 123  # noqa: WPS432
    assert first_arg_to_get_installation_auth.private_key == 'example-key'

    github_initializer_spy.assert_called_once_with(
        auth=mocker.ANY,
        base_url='https://github.com',
    )
    assert isinstance(
        github_initializer_spy.call_args[1]['auth'],
        _FakeAppInstallationAuth,
    )
