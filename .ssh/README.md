# ssh config what I did

1. followed [GitHub: Generating a new SSH key and adding it to the ssh-agent](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
2. created 1Password entry for the key & passphrase
3. added `config` file here bc it doesn't have sensitive data
4. added the key to dotfiles_env repo
5. symlinked it to this repo
    ```zsh
    ln -s /Users/dataders/Developer/dotfiles_env/.ssh/id_ed25519 /Users/dataders/Developer/dotfiles/.ssh/id_ed25519
    ln -s /Users/dataders/Developer/dotfiles_env/.ssh/id_ed25519.pub /Users/dataders/Developer/dotfiles/.ssh/id_ed25519.pub
    ln -s /Users/dataders/Developer/dotfiles_env/.ssh/known_hosts /Users/dataders/Developer/dotfiles/.ssh/known_hosts
    ```
6. symlinked the whole folder to my home folder
    ```zsh
    ln -s /Users/dataders/Developer/dotfiles/.ssh /Users/dataders/.ssh
    ```
7. added the key to GitHub