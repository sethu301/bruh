{ pkgs }: {
  deps = [
    pkgs.libsodium
    pkgs.python3
    pkgs.python3Packages.pynacl
    pkgs.ffmpeg
    pkgs.libopus
    pkgs.libffi
  ];
}

