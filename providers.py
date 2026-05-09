from dataclasses import dataclass, field

DEFAULT_PROVIDER_ICON = "folder-remote-symbolic"


@dataclass
class ProviderField:
    key: str
    label: str
    kind: str
    required: bool = True
    placeholder: str = ""
    choices: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Provider:
    rclone_type: str
    display_name: str
    icon_name: str
    auth_kind: str
    fields: list[ProviderField] = field(default_factory=list)


PROVIDERS: list[Provider] = [
    Provider(
        rclone_type="drive",
        display_name="Google Drive",
        icon_name="gazan-provider-drive",
        auth_kind="oauth",
    ),
    Provider(
        rclone_type="dropbox",
        display_name="Dropbox",
        icon_name="gazan-provider-dropbox",
        auth_kind="oauth",
    ),
    Provider(
        rclone_type="onedrive",
        display_name="OneDrive",
        icon_name="gazan-provider-onedrive",
        auth_kind="oauth",
    ),
    Provider(
        rclone_type="protondrive",
        display_name="Proton Drive",
        icon_name="gazan-provider-protondrive",
        auth_kind="credentials",
        fields=[
            ProviderField("username", "Email", "text", placeholder="you@proton.me"),
            ProviderField("password", "Password", "password"),
        ],
    ),
    Provider(
        rclone_type="s3",
        display_name="Amazon S3",
        icon_name="gazan-provider-s3",
        auth_kind="credentials",
        fields=[
            ProviderField(
                "provider", "Provider", "choice",
                choices=[
                    ("AWS", "Amazon Web Services"),
                    ("Wasabi", "Wasabi"),
                    ("Other", "Other S3-compatible"),
                ],
            ),
            ProviderField("access_key_id", "Access key ID", "text"),
            ProviderField("secret_access_key", "Secret access key", "password"),
            ProviderField(
                "endpoint", "Endpoint URL", "text",
                required=False,
                placeholder="Leave empty for AWS",
            ),
        ],
    ),
    Provider(
        rclone_type="b2",
        display_name="Backblaze B2",
        icon_name="gazan-provider-b2",
        auth_kind="credentials",
        fields=[
            ProviderField("account", "Key ID", "text"),
            ProviderField("key", "Application key", "password"),
        ],
    ),
    Provider(
        rclone_type="sftp",
        display_name="SFTP",
        icon_name="gazan-provider-sftp",
        auth_kind="credentials",
        fields=[
            ProviderField("host", "Host", "text", placeholder="example.com"),
            ProviderField("user", "Username", "text"),
            ProviderField("pass", "Password", "password"),
            ProviderField("port", "Port", "text", required=False, placeholder="22"),
        ],
    ),
    Provider(
        rclone_type="webdav",
        display_name="WebDAV",
        icon_name="gazan-provider-webdav",
        auth_kind="credentials",
        fields=[
            ProviderField("url", "Server URL", "text", placeholder="https://..."),
            ProviderField(
                "vendor", "Server type", "choice",
                choices=[
                    ("nextcloud", "Nextcloud"),
                    ("owncloud", "ownCloud"),
                    ("sharepoint", "SharePoint"),
                    ("other", "Other"),
                ],
            ),
            ProviderField("user", "Username", "text"),
            ProviderField("pass", "Password", "password"),
        ],
    ),
]


def provider_icon(rclone_type: str) -> str:
    for p in PROVIDERS:
        if p.rclone_type == rclone_type:
            return p.icon_name
    return DEFAULT_PROVIDER_ICON
