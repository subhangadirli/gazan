from dataclasses import dataclass, field


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
    icon_file: str | None        # filename in assets/provider-logos/, or None
    auth_kind: str
    fields: list[ProviderField] = field(default_factory=list)
    show_intro: bool = False     # show instructional page before starting OAuth


PROVIDERS: list[Provider] = [
    Provider(
        rclone_type="protondrive",
        display_name="Proton Drive",
        icon_file="proton-drive.svg",
        auth_kind="credentials",
        fields=[
            ProviderField("username", "Email", "text", placeholder="you@proton.me"),
            ProviderField("password", "Password", "password"),
        ],
    ),
    Provider(
        rclone_type="drive",
        display_name="Google Drive",
        icon_file="google-drive.svg",
        auth_kind="oauth",
        show_intro=True,
    ),
    Provider(
        rclone_type="dropbox",
        display_name="Dropbox",
        icon_file="dropbox.svg",
        auth_kind="oauth",
        show_intro=True,
    ),
    Provider(
        rclone_type="onedrive",
        display_name="OneDrive",
        icon_file="microsoft-onedrive.svg",
        auth_kind="oauth",
        show_intro=True,
    ),
    Provider(
        rclone_type="s3",
        display_name="Amazon S3",
        icon_file="amazon-s3.svg",
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
        icon_file="backblaze-svgrepo-com.svg",
        auth_kind="credentials",
        fields=[
            ProviderField("account", "Key ID", "text"),
            ProviderField("key", "Application key", "password"),
        ],
    ),
    Provider(
        rclone_type="webdav",
        display_name="WebDAV",
        icon_file="webdav.png",
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
    Provider(
        rclone_type="webdav",
        display_name="Nextcloud",
        icon_file="nextcloud.svg",
        auth_kind="credentials",
        fields=[
            ProviderField("url", "Server URL", "text", placeholder="https://your.nextcloud.instance/remote.php/webdav"),
            ProviderField("vendor", "Server type", "choice", choices=[("nextcloud", "Nextcloud")]),
            ProviderField("user", "Username", "text"),
            ProviderField("pass", "Password", "password"),
        ],
    ),
    Provider(
        rclone_type="webdav",
        display_name="ownCloud",
        icon_file="owncloud.svg",
        auth_kind="credentials",
        fields=[
            ProviderField("url", "Server URL", "text", placeholder="https://your.owncloud.instance/remote.php/webdav"),
            ProviderField("vendor", "Server type", "choice", choices=[("owncloud", "ownCloud")]),
            ProviderField("user", "Username", "text"),
            ProviderField("pass", "Password", "password"),
        ],
    ),
    Provider(
        rclone_type="webdav",
        display_name="SharePoint",
        icon_file="microsoft-sharepoint.svg",
        auth_kind="credentials",
        fields=[
            ProviderField("url", "Server URL", "text", placeholder="https://your.sharepoint.site/sites/your-site/_layouts/15/sharepoint.aspx"),
            ProviderField("vendor", "Server type", "choice", choices=[("sharepoint", "SharePoint")]),
            ProviderField("user", "Username", "text"),
            ProviderField("pass", "Password", "password"),
        ],
    ),
    Provider(
        rclone_type="sftp",
        display_name="SFTP",
        icon_file=None,
        auth_kind="credentials",
        fields=[
            ProviderField("host", "Host", "text", placeholder="example.com"),
            ProviderField("user", "Username", "text"),
            ProviderField("pass", "Password", "password"),
            ProviderField("port", "Port", "text", required=False, placeholder="22"),
        ],
    ),
]


def find_provider(rclone_type: str) -> Provider | None:
    for p in PROVIDERS:
        if p.rclone_type == rclone_type:
            return p
    return None
