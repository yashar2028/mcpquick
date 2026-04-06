{
  description = "mcpquick sandbox runner nix environments";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        runnerPython = pkgs.python312.withPackages (_ps: [ ]);
      in {
        devShells.mcp-runner = pkgs.mkShell {
          packages = [
            runnerPython
            pkgs.coreutils
            pkgs.jq
          ];
        };
      }
    );
}
