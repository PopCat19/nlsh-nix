{
  description = "Natural language shell - talk to your terminal in plain English";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      pkgsFor = system: nixpkgs.legacyPackages.${system};
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = pkgsFor system;
          python = pkgs.python312;
          pypkgs = python.pkgs;
          nlsh-pkg = pypkgs.buildPythonPackage {
            pname = "nlsh";
            version = "${builtins.substring 0 8 self.lastModifiedDate}-${self.shortRev or "dirty"}";
            pyproject = false;

            src = ./.;

            postPatch = ''
              substituteInPlace nlsh/__init__.py \
                --replace-fail '@VERSION@' '${self.shortRev or "dirty"}' \
                --replace-fail '@DATE@' '${self.lastModifiedDate}'
            '';

            installPhase = ''
              runHook preInstall
              mkdir -p $out/${python.sitePackages}/nlsh/llm
              cp nlsh/*.py $out/${python.sitePackages}/nlsh/
              cp nlsh/llm/*.py $out/${python.sitePackages}/nlsh/llm/
              runHook postInstall
            '';
          };
          python-with-nlsh = python.withPackages (ps: [
            nlsh-pkg
            ps.openai
          ]);
        in
        {
          default =
            pkgs.runCommand
              "nlsh-nix-${builtins.substring 0 8 self.lastModifiedDate}-${self.shortRev or "dirty"}"
              {
                meta = {
                  description = "Natural language shell (NixOS-compatible)";
                  homepage = "https://github.com/PopCat19/nlsh-nix";
                  license = pkgs.lib.licenses.mit;
                  mainProgram = "nlsh";
                  platforms = supportedSystems;
                };
              }
              ''
                            mkdir -p $out/bin
                            cat > $out/bin/nlsh << 'EOF'
                #!/bin/sh
                exec ${python-with-nlsh.interpreter} -m nlsh "$@"
                EOF
                            chmod +x $out/bin/nlsh
              '';
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = pkgsFor system;
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.python312
              pkgs.python312Packages.openai
              pkgs.python312Packages.black
              pkgs.nixfmt-rfc-style
            ];
          };
        }
      );
    };
}
