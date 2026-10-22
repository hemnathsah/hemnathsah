# Install this animated profile README

This kit is tailored to GitHub user `hemnathsah` and the article you shared. It includes a terminal-style profile README, animated SVG assets, scripts to fetch and render the contribution calendar, an optional photo-to-ASCII generator, and a daily GitHub Actions workflow.

## Important: use the profile repository

Upload these files to **https://github.com/hemnathsah/hemnathsah** (repository name exactly `hemnathsah`). Do **not** upload this kit over `hemnathsah.github.io`; that separate repository hosts your live website.

## Windows installation (recommended)

1. Download and extract `hemnathsah-profile-readme-kit.zip` to a folder such as `C:\Users\<you>\Downloads\hemnathsah-profile-readme-kit`.
2. Make a backup of the current profile README: open `https://github.com/hemnathsah/hemnathsah/blob/main/README.md`, click **Raw**, and save it as `README-before-terminal-design.md` somewhere outside the repository.
3. Open PowerShell. If Git is installed, run the following, adjusting the extracted ZIP folder path if necessary:

   ```powershell
   $Kit = "$HOME\Downloads\hemnathsah-profile-readme-kit"
   $Repo = "$HOME\Documents\hemnathsah-profile"
   git clone https://github.com/hemnathsah/hemnathsah.git $Repo
   Get-ChildItem -LiteralPath $Kit -Force | Copy-Item -Destination $Repo -Recurse -Force
   Set-Location $Repo
   git status --short
   git add README.md SETUP_GUIDE.md scripts data .github hemnath-ascii.svg info-card.svg contrib-heatmap.svg
   git commit -m "Add animated terminal-style profile README"
   git push
   ```

   If `git clone` says the folder already exists, choose a different destination folder. If `git push` opens GitHub authentication, complete the normal Git Credential Manager/browser login; do not put passwords or tokens in the command.

4. Open [your profile](https://github.com/hemnathsah) and confirm the README layout appears.
5. Open the repository's **Actions** tab. If prompted, enable GitHub Actions for the repository. Choose **Update profile art** → **Run workflow** to fetch your real contribution data and update the heatmap.
6. Open the workflow run. Wait for the run to finish successfully. It should commit updated `data/contributions.json` and `contrib-heatmap.svg`.

## If you prefer GitHub's website

You can upload files from the extracted folder via **Add file → Upload files**, but preserve the directory structure. In particular, the workflow must be at `.github/workflows/update-profile-art.yml`, and the Python scripts must remain in `scripts/`. For a kit with several folders, using Git locally is more reliable than uploading individual files through the browser.

## Generate your own ASCII portrait (optional)

The included `hemnath-ascii.svg` is a non-personal terminal placeholder; no photo was supplied, so it does not pretend to be your likeness.

1. Copy a photo you are comfortable making public to the repository working folder and name it `source-photo.jpg` (you may use another filename).
2. Install Pillow locally: `python -m pip install -r scripts/requirements-portrait.txt`
3. Run: `python scripts/make_ascii_svg.py --input source-photo.jpg --output hemnath-ascii.svg`
4. Preview the SVG locally, then commit and push the changed `hemnath-ascii.svg`.

The photo is processed locally by the script and is not uploaded by the script. Do not commit the source photo unless you intentionally want it public; delete it from the working folder after generation if you prefer.

## How the contribution graph works

- `scripts/fetch_contributions.py` reads the public GitHub contribution-calendar HTML for `hemnathsah`; it requires no personal access token.
- `scripts/render_heatmap_svg.py` turns that captured data into an animated 53-week SVG.
- `.github/workflows/update-profile-art.yml` runs on a daily schedule and can also be launched manually from the Actions tab. It uses the workflow's built-in `GITHUB_TOKEN` permission to commit refreshed assets; you do not need to create or paste a token.
- GitHub's public HTML can change. If the data fetcher reports that it could not find calendar cells, inspect the workflow log before changing anything else. The workflow should fail visibly rather than replacing real data with invented counts.

## Customize the profile

Edit these lines in `scripts/make_info_card.py` if your current focus or preferred stack changes. Edit the project descriptions in `README.md` before publishing if any line no longer reflects your work. The description intentionally marks CCNA-Diagram-AI and other ongoing work as in development and does not claim unverified metrics or credentials.
