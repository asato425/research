from research.tools.github import GitHubAPIClient

def main():
    client = GitHubAPIClient(repo_url="https://github.com/asato425/test")
    
    result = client.clone_repository()
    print("Clone result:", result)

    result = client.create_empty_file("summary.md")
    print("Create empty file result:", result)

    result = client.push_changes(message="Add summary.md")
    print("Push changes result:", result)

    result = client.delete_cloned_repository()
    print("Delete cloned repository result:", result)

if __name__ == "__main__":
    main()
