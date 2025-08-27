from research.tools.github import GitHubAPIClient

def main():
    client = GitHubAPIClient(repo_url="https://github.com/asato425/test1")
    
    result = client.clone_repository()
    print("Clone result:", result)

    file_name = "test.py"

    client.create_working_branch("feature/" + file_name)
    client.create_yml_file(file_name)
    client.push_changes(message="branch for " + file_name)
    client.delete_cloned_repository()

if __name__ == "__main__":
    main()
