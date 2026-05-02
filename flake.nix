{
  description = "Natural language shell - talk to your terminal in plain English";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      pkgsFor = system: nixpkgs.legacyPackages.${system};
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = pkgsFor system;
          python = pkgs.python312;
          pypkgs = python.pkgs;
        in
        {
          default = pypkgs.buildPythonApplication {
            pname = "nlsh-nix";
            version = "0.1.0";
            pyproject = false;

          src = ./.;

          propagatedBuildInputs = [ pypkgs.google-genai ];

          installPhase = ''
            runHook preInstall
            mkdir -p $out/bin
            cp nlsh.py $out/bin/nlsh
            chmod +x $out/bin/nlsh
            runHook postInstall
          '';

          meta = {
            description = "Natural language shell (NixOS-compatible)";
            homepage = "https://github.com/PopCat19/nlsh-nix";
            license = pkgs.lib.licenses.mit;
            mainProgram = "nlsh";
            platforms = supportedSystems;
          };
        };
      });

      devShells = forAllSystems (system:
        let
          pkgs = pkgsFor system;
        in
        {
          default = pkgs.mkShell {
            packages = [ pkgs.python312 pkgs.python312Packages.google-genai ];
          };
        }
      );
    };
}