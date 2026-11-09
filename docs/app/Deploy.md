# Deploy: going live on Azure

The whole app (the frontend, the API and the model) runs as one container on Azure Container Apps. GitHub builds the container and tests it, and GitHub's registry stores it. Azure for Students pays for the run, with no card. Your laptop builds and runs nothing.

Do the steps in order. Azure's screens change now and then, so if a label here does not match, look for the closest one.

## Before you start

1. You need an Azure for Students subscription. Sign up at https://azure.microsoft.com/en-in/free/students/ and sign in with a personal Microsoft account, not your college one, so the subscription outlives your college address.
2. Register two services, once. In the Azure portal (https://portal.azure.com), open **Subscriptions**, then your **Azure for Students** subscription, then **Resource providers** under **Settings**. Search for `Microsoft.App`, select it and click **Register**. Do the same for `Microsoft.OperationalInsights`. Wait until both say **Registered**.

## 1. Upload the model

The model is 486 MB, too big for git. A GitHub release can hold it as a file, and the build downloads it from there.

1. Check the file in Git Bash. The size must be `509869238` bytes, and the hash must start with `28d43542` and end with `cbe758`:

   ```bash
   ls -l /c/dev/clauseanchor-model/clauseanchor-candidate-prototype-v0.zip
   ```

   ```bash
   sha256sum /c/dev/clauseanchor-model/clauseanchor-candidate-prototype-v0.zip
   ```

2. Open https://github.com/TheMEGALODON55681/clauseanchor/releases/new.
3. Click **Choose a tag**, type `model-v0`, and click **Create new tag: model-v0 on publish**. Leave the target as `main`.
4. Set the title to `Model v0 (candidate prototype)`.
5. Write one line in the description box, such as `Model used by the live deployment. Not source code.`
6. Drag `clauseanchor-candidate-prototype-v0.zip` into the box at the bottom that says **Attach binaries by dropping them here or selecting them**. This is the assets area, not the description. Wait until the upload bar finishes and the file name shows with its size.
7. Untick **Set as the latest release** if it is ticked, then click **Publish release**.
8. Check that the release page lists the zip under **Assets**.

## 2. Build the image

1. Commit and push the changes that add the workflow. GitHub can run it only once the file is on `main`.
2. In the repository, open the **Actions** tab. If GitHub says workflows are disabled, click the button that enables them.
3. In the left list, click **image**. Click **Run workflow**, keep the branch as `main`, and click the green **Run workflow** button.
4. Open the new run and its job. The steps run in this order: download the model and check its hash, build the image, start the container, run the smoke test, check memory, publish. Expect 15 to 40 minutes. The workflow has not run yet, so that is an estimate.
5. A green tick means the image is published. Open the run's **Summary** to see the image size and the peak memory. A red cross means a step failed: open that step and copy its last 50 lines. Read them before you run the workflow again.
6. Make the image public, because Azure pulls it with no password. Open your GitHub profile, then the **Packages** tab, then **clauseanchor**, then **Package settings**. Under **Danger Zone**, click **Change visibility**, choose **Public**, type `clauseanchor` to confirm, and click the button. Public means anyone can download the image, and the model is inside it. Check with Tanishq that the model may be public before you do this.

The image is `ghcr.io/themegalodon55681/clauseanchor:latest`.

## 3. Create the app on Azure

1. In the portal, search for **Container Apps**, open it, and click **Create**, then **Container App**.
2. **Basics** tab:

   | Field | Value |
   |---|---|
   | Subscription | Azure for Students |
   | Resource group | **Create new**, name it `clauseanchor-rg` |
   | Container app name | `clauseanchor` (lowercase, it becomes part of the link) |
   | Deployment source | Container image |
   | Region | One near India, such as **Central India** or **South India** |
   | Container Apps environment | **Create new**, name it `clauseanchor-env`, keep the **Consumption** plan, leave zone redundancy off, click **Create** |

   A student subscription allows only some regions. An error that mentions a policy means the region you picked is not one of them, so pick another from the **Region** list. To see the allowed regions, open **Policy**, then **Assignments**, and open the assignment that limits regions.
3. **Container** tab:

   | Field | Value |
   |---|---|
   | Use quickstart image | untick |
   | Name | `clauseanchor` |
   | Image source | Docker Hub or other registries |
   | Image type | Public |
   | Registry login server | `ghcr.io` |
   | Image and tag | `themegalodon55681/clauseanchor:latest` |
   | CPU and memory | 2 CPU cores, 4 Gi memory |
   | Environment variables | none. The image sets them for 2 CPUs. If you change the CPU count, set `OMP_NUM_THREADS` and `MKL_NUM_THREADS` to the same number |

4. **Ingress** tab: turn ingress **on**, accept traffic **from anywhere**, type **HTTP**, target port `8000`, and leave **Allow insecure connections** off.
5. Click **Review + create**, then **Create**. When it says the deployment is complete, which takes a few minutes, click **Go to resource**.
6. Let the app sleep when nobody uses it. Open **Scale** (it may be called **Scale and replicas**), set **Min replicas** to `0` and **Max replicas** to `1`, and save. Keep the maximum at 1: sessions live in the memory of one copy, so a second copy could not find them.
7. Give the model time to load with a startup probe. Open **Containers**, then **Edit and deploy**, select the container and open **Health probes**. Enable the **Startup probe** with transport **HTTP**, path `/api/v1/ready`, port `8000`, initial delay `30` seconds, period `30` seconds and failure threshold `10`. That gives the model about 5 minutes to load, and Azure sends no visitors until the probe passes. Leave the other probes as they are. Save and create the new revision.
8. Open **Overview** and copy the **Application Url**. It looks like `https://clauseanchor.something.centralindia.azurecontainerapps.io`.

## 4. Check it

Open the Application Url. The first visit takes 1 to 3 minutes while Azure starts the container and loads the model, so wait and refresh if you see an error. Then work through this list with a PDF and a Word file of your own:

- [ ] The landing page loads, and the browser console shows no red error.
- [ ] **Review a contract** opens the upload step. Upload the PDF. The page shows its name and page count, then a ready state.
- [ ] Choose the Word file in its place. The page shows the new name and no error.
- [ ] Step 2 shows a notice that this build does not use your side yet. Pick any role and party, or "None of these", and go on.
- [ ] Step 3 lists the categories in seven groups. Start review stays disabled until you pick one. Pick three, and start.
- [ ] A band shows "Checking categories" and "N of M steps". When it ends, marks appear on the text.
- [ ] Select a mark. The panel shows the quoted wording and "Confidence not validated". It shows no burden or benefit label.
- [ ] Start a review with every category on a long file, then press **Cancel**. The review stops.
- [ ] **Delete document**, then confirm. The Expired page opens and says the contract was deleted.

If something fails, open the app in the portal, then **Monitoring**, then **Log stream**, repeat the step, and copy the last lines.

## 5. Demo day

- The morning of the demo, set **Min replicas** to `1` under **Scale**, and open the link once. The app stays awake, so there is no cold start.
- After the demo, set **Min replicas** back to `0` the same day.
- Do not change any setting during the demo. A change makes a new revision and ends every session.

## 6. Watch the cost

The Consumption plan gives each subscription 180,000 vCPU-seconds and 360,000 GiB-seconds free every month. At 2 vCPU and 4 GiB, one running hour uses 7,200 vCPU-seconds and 14,400 GiB-seconds, so the grant covers about 25 hours a month. When nobody uses the app, it scales to zero a few minutes after the last visit and uses nothing.

A replica that never sleeps uses 172,800 vCPU-seconds in one day. That is nearly the whole monthly grant, so do not leave **Min replicas** at 1. Azure bills an idle replica at a lower rate, so that figure is the upper bound.

Anything over the grant comes out of your Azure for Students credit. To see what is left, search the portal for **Cost Management + Billing** and open **Credits**. You can also open https://www.microsoftazuresponsorships.com/balance. To get an email before it runs low, open **Cost Management**, then **Budgets**, then **Add**, and set an amount of `10` with an alert at 80 percent.

## If something goes wrong

| Problem | Fix |
|---|---|
| "Not registered to use namespace Microsoft.App" | Register the two services under **Before you start** |
| "Unauthorized" or "manifest unknown" when Azure pulls the image | Make the package public (step 2.6) and check the image name in step 3 |
| The app keeps restarting | Check that memory is 4 Gi and the startup probe's failure threshold is 10, then read the **Log stream** |
| "Session expired" straight after a wait | Normal after the app has slept: sessions live in memory. Start a new review |
