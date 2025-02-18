1. moved things to dotfiles_env
   1. `profiles.yml`
   2. `.user.yml`
   3. `.dbt_cloud.yml`
2. symlinked to dotfiles
    ```zsh
    ln -s /Users/dataders/Developer/dotfiles_env/.dbt/profiles.yml /Users/dataders/Developer/dotfiles/.dbt/profiles.yml
    ln -s /Users/dataders/Developer/dotfiles_env/.dbt/.user.yml /Users/dataders/Developer/dotfiles/.dbt/.user.yml
    ln -s /Users/dataders/Developer/dotfiles_env/.dbt/.dbt_cloud.yml /Users/dataders/Developer/dotfiles/.dbt/.dbt_cloud.yml
    ```
3. symlinked to home
   ```zsh
    ln -s /Users/dataders/Developer/dotfiles/.dbt /Users/dataders/.dbt
    ```