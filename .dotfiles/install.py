from pyinfra.operations import apt, brew, server, files, git
from pathlib import Path
from pyinfra import host
from pyinfra.facts.server import Home
from pyinfra import facts as facts
from pathlib import PurePosixPath
import shlex


def main():
    configure_repos()
    install_packages()
    brew_installs()
    script_installs()
    install_vundle()


def configure_repos():
    """
    Configure OS repos (apt, pacman, yum etc.)
    """
    apt.ppa(
        src="ppa:appimagelauncher-team/stable",
        name="Add appimagelauncher repo",
        sudo=True,
    )
    apt.key(
        name="Add signal desktop key",
        src="https://updates.signal.org/desktop/apt/keys.asc",
        sudo=True,
    )
    apt.repo(
        "deb [arch=amd64] https://updates.signal.org/desktop/apt xenial main",
        present=True,
        filename="signal-xenial",
        sudo=True,
    )


def brew_installs():
    brew.packages(
        name="Install lazygit",
        packages=["jesseduffield/lazygit/lazygit"],
    )
    if not host.get_fact(facts.server.Which, "fzf"):
        brew.packages(
            name="Install fzf",
            packages=["fzf"],
        )
        # --all is needed. Otherwise, `install` will have an interactive prompt
        server.shell(commands=["$(brew --prefix)/opt/fzf/install --all"])


def script_installs():
    server.shell(
        name="Install starship",
        commands=[
            'sh -c "$(curl -fsSL https://starship.rs/install.sh)" -- --yes',
        ],
        sudo=True,
    )

    install_joplin()

    install_vim_plug()
    install_delta()
    install_vscode()
    install_nerd_fonts()
    install_rust()

    install_alacritty()
    install_kitty()
    install_tdrop()

    install_pyenv()
    install_neovim_python()


def install_neovim_python():
    server.shell(
        commands=[
            # exit 0 so that we don't throw an error if there isn't
            # an activated pyenv environment
            "pyenv deactivate 2>/dev/null; exit 0",
            "python3.6 -m pip install neovim",
        ]
    )


def install_pyenv():
    existing_versions = set(
        host.get_fact(
            facts.server.Command,
            "pyenv versions --bare",
        ).split()
    )
    _py36_ver = "3.6.13"
    if _py36_ver not in existing_versions:
        server.shell(
            name="Install python3.6",
            commands=[f"CC=clang pyenv install {_py36_ver}"],
        )
    _versions = [
        "3.7.12",
        "3.8.12",
        "3.9.9",
        "3.10.0",
    ]
    for _version in _versions:
        if _version in existing_versions:
            continue
        server.shell(
            name=f"Install python=={_version}",
            commands=[f"pyenv install {_version}"],
        )

    server.shell(
        name="pyenv global",
        commands=[f"pyenv global {_py36_ver} {' '.join(_versions)}"],
    )
    install_black(versions=_versions)


def install_black(*, versions):
    for version in versions:
        server.shell(
            name="install black",
            commands=[f"PYENV_VERSION={version} python -m pip install black"],
        )


def install_joplin():
    if host.get_fact(facts.files.File, _get_home() / ".joplin" / "VERSION"):
        return
    server.shell(
        name="install joplin",
        commands=[
            "wget -O - https://raw.githubusercontent.com/laurent22/joplin/dev/Joplin_install_and_update.sh "
            "| TERM=linux bash --login -s -- --silent"
        ],
    )


def install_tdrop():
    if host.get_fact(facts.server.Which, "tdrop"):
        return
    tmpdir = "/tmp/tdrop"
    git.repo("https://github.com/noctuid/tdrop", tmpdir)
    server.shell(
        name="installing tdrop",
        commands=["make install"],
        sudo=True,
        chdir=tmpdir,
    )


def install_rust():
    server.shell(
        name="Install rust",
        commands=["curl https://sh.rustup.rs -sSf | sh -s -- -y"],
    )


def install_vscode():
    if host.get_fact(facts.server.Which, "code"):
        print("vscode already installed")
        return

    download_path = "/tmp/vscode.deb"
    files.download(
        "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64",
        download_path,
        name="Downloading vscode.deb",
    )
    server.shell(
        name="Installing vscode",
        commands=[f"dpkg -i {download_path}"],
        sudo=True,
    )


def install_vim_plug():
    if not host.get_fact(
        facts.files.File, _get_home() / ".vim" / "autoload" / "plug.vim"
    ):
        print("installing vim-plug")
        server.shell(
            name="Install [vim plug](https://github.com/junegunn/vim-plug)",
            commands=[
                "curl -fLo ~/.vim/autoload/plug.vim --create-dirs "
                "https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim"
            ],
        )
    nvim_path = (
        _get_home() / ".local" / "share" / "nvim" / "site" / "autoload" / "plug.vim"
    )
    if not host.get_fact(
        facts.files.File,
        str(nvim_path),
    ):
        print("installing vim-plug for neovim")
        files.directory(nvim_path.parent)
        files.download(
            "https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim",
            nvim_path,
        )

    print("installing plugins with vim-plug")
    server.shell(
        name="Install vim plugins with vim plug",
        commands=[
            "vim -E -s +PlugInstall +visual +qall",
            "vim -E -s +PlugUpdate +visual +qall",
            "nvim +'PlugInstall --sync' +qa",
            "nvim +'PlugUpdate --sync' +qa",
        ],
    )


def install_delta():
    if host.get_fact(facts.server.Which, "delta"):
        return

    download_path = "/tmp/git-delta.deb"
    files.download(
        "https://github.com/dandavison/delta/releases/download/0.10.3/git-delta_0.10.3_amd64.deb",
        download_path,
    )
    server.shell(
        name="install [git-delta](https://github.com/dandavison/delta)",
        commands=[f"dpkg -i {download_path}"],
        sudo=True,
    )


def _get_home() -> Path:
    return PurePosixPath(host.get_fact(Home))


def install_packages():
    """
    Install packages with system's package manager
    (e.g. apt, pacman)
    """
    apt.update(sudo=True)
    packages = [
        "appimagelauncher",
        "bat",
        "ddgr",
        "direnv",
        "golang-go",
        "neovim",
        "podman",
        "python3-pip",
        "signal-desktop",
        "sxhkd",
        "tmux",
        "unzip",
        "virtualbox",
        "xclip",
        "xdotool",
    ]
    packages = packages + python_build_dependencies()
    server.packages(
        packages=packages,
        sudo=True,
    )


def python_build_dependencies():
    return [
        "libbz2-dev",
        "libc6-dev",
        "libgdbm-dev",
        "libncursesw5-dev",
        "libsqlite3-dev",
        "libssl-dev",
        "tk-dev",
        "build-essential",
        "clang",
        "curl",
        "git",
        "libbz2-dev",
        "libffi-dev",
        "liblzma-dev",
        "libncurses5-dev",
        "libncursesw5-dev",
        "libreadline-dev",
        "libsqlite3-dev",
        "libssl-dev",
        "llvm",
        "make",
        "python3-openssl",
        "tk-dev",
        "wget",
        "xz-utils",
        "zlib1g-dev",
    ]


def install_vundle():
    vundle_dir = str(
        PurePosixPath(host.get_fact(Home)) / ".vim" / "bundle" / "Vundle.vim"
    )
    if host.get_fact(facts.files.Directory, vundle_dir):
        return
    server.shell(
        commands=[
            shlex.join(
                [
                    "git",
                    "clone",
                    "https://github.com/gmarik/Vundle.vim.git",
                    vundle_dir,
                ],
            ),
            "vim +PluginInstall +qall",
            "vim +PluginUpdate +qall",
            "nvim +PluginInstall +qall",
            "nvim +PluginUpdate +qall",
        ]
    )


def install_nerd_fonts():
    fc_list_result = host.get_fact(
        facts.server.Command,
        # exit 0 so pyinfra doesn't error out
        "fc-list | grep -i nerd; exit 0",
    )
    if fc_list_result and fc_list_result.strip():
        return
    tmp_firacode = "/tmp/firacode.zip"
    files.download(
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.1.0/FiraCode.zip",
        tmp_firacode,
    )
    fonts_dir = str(_get_home() / ".local" / "share" / "fonts")
    files.directory(fonts_dir, name="Create ~/.local/share/fonts")
    server.shell(
        name="Install fira code", commands=[f"unzip {tmp_firacode} -d {fonts_dir}"]
    )


def install_alacritty():
    if host.get_fact(facts.server.Which, "alacritty"):
        return
    alacritty_dir = "/tmp/alacritty"
    files.directory(alacritty_dir, present=False)

    server.shell(
        name="cloning alacritty",
        commands=[
            shlex.join(
                [
                    "git",
                    "clone",
                    "https://github.com/alacritty/alacritty.git",
                    alacritty_dir,
                ]
            )
        ],
    )

    server.shell(
        name="Check rust compiler version",
        commands=[
            "rustup override set stable",
            "rustup update stable",
        ],
    )
    server.packages(
        name="Install other alacritty dependencies",
        sudo=True,
        packages=[
            "cmake",
            "pkg-config",
            "libfreetype6-dev",
            "libfontconfig1-dev",
            "libxcb-xfixes0-dev",
            "libxkbcommon-dev",
            "python3",
        ],
    )
    server.shell(
        name="cargo build alacritty",
        commands=[
            f"cd {alacritty_dir}; cargo build --release",
        ],
    )

    output = host.get_fact(
        facts.server.Command,
        "infocmp alacritty >/dev/null; echo $?",
    )
    if output != "0":
        print(f"infocmp alacritty {output=}")
        server.shell(
            name="running tic -xe alacritty",
            commands=["tic -xe alacritty,alacritty-direct extra/alacritty.info"],
            sudo=True,
        )
    server.shell(
        name="Install Alacritty Desktop Entry",
        sudo=True,
        commands=[
            " && ".join(
                [
                    f"cd {alacritty_dir}",
                    "cp target/release/alacritty /usr/local/bin",
                    "cp extra/logo/alacritty-term.svg /usr/share/pixmaps/Alacritty.svg",
                    "desktop-file-install extra/linux/Alacritty.desktop",
                    "update-desktop-database",
                ]
            )
        ],
    )


def install_kitty():
    server.shell(
        name="Install Kitty",
        commands=[
            "curl -L https://sw.kovidgoyal.net/kitty/installer.sh | sh /dev/stdin launch=n",
        ],
    )

    # Create a symbolic link to add kitty to PATH (assuming ~/.local/bin is in
    # your PATH)
    files.link(
        path=str(_get_home() / ".local" / "bin" / "kitty"),
        target=str(_get_home() / ".local" / "kitty.app" / "bin" / "kitty"),
    )
    # ln -s ~/.local/kitty.app/bin/kitty ~/.local/bin/
    # Place the kitty.desktop file somewhere it can be found by the OS
    kitty_desktop_src = (
        _get_home()
        / ".local"
        / "kitty.app"
        / "share"
        / "applications"
        / "kitty.desktop"
    )
    kitty_desktop_dst = (
        _get_home() / ".local" / "share" / "applications" / "kitty.desktop"
    )
    server.shell(commands=[f"cp {kitty_desktop_src} {kitty_desktop_dst}"])
    # Update the path to the kitty icon in the kitty.desktop file

    kitty_icon = (
        _get_home()
        / ".local"
        / "kitty.app"
        / "share"
        / "icons"
        / "hicolor"
        / "256x256"
        / "apps"
        / "kitty.png"
    )
    sed_string = f"s|Icon=kitty|Icon={kitty_icon}|g"
    server.shell(
        name="Remapping kitty icon with sed",
        commands=[f'sed -i "{sed_string}" {kitty_desktop_dst}'],
    )


# TODO - Clean up readme + use just python to bootstrap
# TODO - Install docker, podman, and earthly
# TODO - Look into another dotfile CLI tool
# TODO - Install libevdev key mapping


main()
