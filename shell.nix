with import <nixpkgs> {};

pkgs.mkShell {
  buildInputs = with python3Packages; [
    flake8
    ipython
    jedi
    pip
    requests
    rope
  ];
}
