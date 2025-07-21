# PeerPilot - SciReview Agent (Kiro Hackathon Submission)

## Project Overview

**PeerPilot** is an intelligent AI agent designed to streamline and enhance the scientific article review process. This submission for the "Code with Kiro" Hackathon demonstrates a Minimum Viable Product (MVP) that automates the initial validation of submitted articles against journal guidelines and intelligently suggests potential reviewers.

The traditional peer review process is often slow, manual, and prone to inconsistencies. PeerPilot aims to alleviate these bottlenecks by leveraging Artificial Intelligence to provide rapid, data-driven assistance to journal editors, allowing them to focus on high-level editorial decisions.

## Problem Solved

* **Time-Consuming Initial Screening:** Editors spend significant time manually checking if submitted articles adhere to basic journal guidelines (thematic fit, abstract word count, required sections).
* **Inefficient Reviewer Assignment:** Identifying suitable reviewers is a laborious task, often relying on personal networks or superficial keyword matching, leading to delays and suboptimal reviewer choices.

## Our Solution: PeerPilot

PeerPilot addresses these challenges by providing an automated, multi-step workflow:

1.  **Automated Article Ingestion:** Seamlessly accepts article PDFs.
2.  **Intelligent Content Extraction:** Extracts raw text from PDFs for analysis.
3.  **Guideline Compliance Validation:** Automatically checks articles against predefined journal rules using AI.
4.  **Basic Reviewer Suggestion:** Proposes suitable reviewers based on article content.

## How Kiro Empowered This Project

As a researcher with limited deep programming experience, building an AI agent from scratch seemed daunting. **Kiro has been an absolute game-changer**, acting as my AI co-developer, enabling me to focus on the problem domain and the logic, rather than getting bogged down in boilerplate code and infrastructure setup.

Kiro's key contributions to PeerPilot include:

* **Rapid AWS Integration:** Kiro seamlessly generated the necessary Python code to interact with Amazon S3 (for file storage) and Amazon Textract (for PDF text extraction), abstracting away complex API calls.
* **Data Structure Definition (`Specs`):** Kiro helped define the data models for journal rules and reviewer profiles, ensuring structured and manageable data.
* **AI Logic Orchestration:** Kiro facilitated the integration with Amazon Bedrock, allowing us to leverage powerful Large Language Models (LLMs) for intelligent content validation based on dynamic rules.
* **Automated Workflow (`Hooks`):** Kiro's `hooks` feature was instrumental in chaining together the various steps of the agent (PDF upload -> text extraction -> validation -> reviewer suggestion) into a fully automated pipeline, triggered by simple events like a new file upload to S3.
* **Quick UI Prototyping:** Kiro assisted in generating a basic web interface, enabling rapid demonstration of the agent's capabilities without extensive frontend development.

## Architecture and AWS Services Used

PeerPilot leverages the following AWS services, orchestrated and integrated with the help of Kiro:

* **Amazon S3:** For secure and scalable storage of raw article PDFs, journal guidelines (YAML/JSON), reviewer data (CSV/JSON), and generated reports.
    * **Bucket Name:** `peerpilot-kiro-data`
    * **Key Prefixes:**
        * `articulos-entrada/` (for incoming PDFs)
        * `normas-revistas/` (for journal rule definitions)
        * `revisores-basico/` (for basic reviewer profiles)
        * `resultados-revisiones/` (for generated reports)
* **Amazon Textract:** For highly accurate text extraction from submitted PDF articles.
* **Amazon Bedrock:** To access powerful Large Language Models (LLMs) like Anthropic Claude for intelligent content validation and analysis against journal guidelines.
* **(Potentially) AWS Lambda:** Kiro likely deploys parts of the workflow as serverless Lambda functions, ensuring scalability and cost-efficiency.

## How to Run PeerPilot (Kiro MVP)

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/YOUR_GITHUB_USERNAME/PeerPilot-Kiro-Hackathon.git](https://github.com/YOUR_GITHUB_USERNAME/PeerPilot-Kiro-Hackathon.git)
    cd PeerPilot-Kiro-Hackathon
    ```
2.  **AWS Configuration:**
    ---
    ### AWS Setup Guide for PeerPilot

    Here are the steps to configure the integration with AWS S3:

    #### 1. AWS Credentials Setup
    You have a few options for AWS credentials:
    **Option A: Environment Variables (Recommended for development)**
    ```bash
    # Edit your .env file with your actual AWS credentials
    # You can get these from AWS IAM console
    ```
    **Option B: AWS CLI Configuration**
    ```bash
    # Install AWS CLI if you haven't already
    pip install awscli
    # Configure your credentials
    aws configure
    ```
    **Option C: IAM Roles (For production/EC2)**
    If running on EC2, you can use IAM roles instead of hardcoded credentials.

    #### 2. Get Your AWS Credentials
    Go to [AWS IAM Console](https://console.aws.amazon.com/iam/home#/users)
    * Click "Users" → "Create User"
    * Give it a name like `peerpilot-s3-user`
    * Attach the policy `AmazonS3FullAccess` (or create a custom policy for just your bucket)
    * Go to "Security credentials" tab → "Create access key"
    * Choose "Application running outside AWS"
    * Copy the Access Key ID and Secret Access Key

    #### 3. Update Your Environment
    Edit your `.env` file with your actual credentials:
    ```
    AWS_ACCESS_KEY_ID=AKIA...your_actual_key
    AWS_SECRET_ACCESS_KEY=your_actual_secret_key
    AWS_DEFAULT_REGION=us-east-1
    S3_BUCKET_NAME=peerpilot-kiro-data
    ```

    #### 4. Install Dependencies
    ```bash
    pip install -r requirements.txt
    ```

    #### 5. Test Your Setup
    ```bash
    python test_s3_setup.py
    ```
    This will:
    * Create the `peerpilot-kiro-data` bucket if it doesn't exist
    * Test upload, download, list, and delete operations
    * Clean up test files

    #### 6. S3 Bucket Structure
    Your bucket will be organized like this:
    ```
    peerpilot-kiro-data/
    ├── articulos-entrada/     # Incoming PDF articles
    ├── normas-revistas/       # Journal guidelines (YAML/JSON)
    ├── revisores-basico/      # Reviewer profiles (CSV/JSON)
    └── resultados-revisiones/ # Generated reports
    ```

    #### 7. Security Best Practices
    * Never commit your `.env` file to git (it's already in `.gitignore`)
    * Use IAM policies with minimal required permissions
    * Consider using AWS IAM roles for production deployments
    * Rotate your access keys regularly

    Your S3 client is already configured with all the methods you'll need:
    * `upload_file()` - Upload PDFs and data files
    * `download_file()` - Retrieve files for processing
    * `list_files()` - Browse bucket contents
    * `delete_file()` - Clean up temporary files
    * `create_bucket_if_not_exists()` - Automatic bucket setup

    Once you've updated your `.env` file with real AWS credentials, run the test script to verify everything works. The bucket will be created automatically on first use!
    ---

3.  **Install Kiro and Dependencies:**
    ```bash
    pip install kiro-sdk # and any other dependencies Kiro suggests
    ```
4.  **Prepare Data:**
    * Place your `journal_rules.yaml` file (following the defined spec) in the `peerpilot-kiro-data/normas-revistas/` S3 prefix.
    * Place your `reviewers.csv` (or JSON) file in the `peerpilot-kiro-data/revisores-basico/` S3 prefix.
5.  **Run the UI/Trigger the Workflow:**
    * Follow the instructions generated by Kiro for running the simple web UI (e.g., `python app.py`).
    * Upload a PDF article through the UI. This will trigger the Kiro-orchestrated workflow.
    * Alternatively, you can manually upload a PDF to `peerpilot-kiro-data/articulos-entrada/` to trigger the workflow via S3 event hooks.
6.  **View Results:**
    * The processed report will appear in the UI, or you can find the generated report file in `peerpilot-kiro-data/resultados-revisiones/`.

## Future Enhancements (Beyond Kiro Hackathon)

This MVP is a stepping stone. Future plans for PeerPilot include:

* **Advanced Reviewer Matching:** Leveraging vector databases (like TiDB Cloud's Vector Search) for highly semantic and accurate reviewer matching.
* **Multi-Lingual Support:** Expanding the agent's capabilities to process articles and generate reports in multiple languages (e.g., Spanish), enhancing global applicability.
* **Full Editorial Workflow Automation:** Integrating with external APIs for automated email invitations, reminder systems, and tracking reviewer responses.
* **Rich User Interface:** Developing a more comprehensive and interactive dashboard for editors using frameworks like Streamlit.

## Contact

Gerlyn Eduardo Duarte
gerlyn@ula.ve

---

### Git Troubleshooting History

During the initial setup and development, we encountered and resolved the following common issues related to Git and security:

-   **Issue: "Cannot push references to remote, run a pull" (No se puede enviar referencias al remoto, ejecutar un pull):**
    -   **Cause:** Conflict in the commit history with the remote repository.
    -   **Resolution:** Resolved by executing `git pull origin main` to synchronize changes before pushing.

-   **Issue: "Push cannot contain secrets" (GitHub Push Protection):**
    -   **Cause:** The `.env.example` file was accidentally included in Git history containing secret patterns (even with placeholders), which was detected by GitHub's push protection in an earlier commit.
    -   **Resolution:**
        1.  The content of `.env.example` was verified and cleaned to ensure it only contained generic placeholders.
        2.  `.env.example` was added to the `.gitignore` file to prevent Git from tracking this file in the future.
        3.  Git history was rewritten using the command `git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env.example" --prune-empty --tag-name-filter cat -- --all` to permanently remove all instances of the `.env.example` file that might have contained secrets from **all past commits**.
        4.  Finally, the remote repository was force-updated by executing `git push --force origin main` to overwrite the old history with the new, clean history.
    -   **Importance:** This is a fundamental security practice to prevent accidental exposure of credentials and other sensitive data in public repositories.