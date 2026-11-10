# Deploy: going live on Azure

The whole app (the frontend, the API and the model) runs as one container on Azure Container Apps in Central India. GitHub builds the container and tests it, and GitHub's registry stores it. Azure for Students pays for the run, with no card. You work from Azure Cloud Shell in your browser, so your laptop builds and runs nothing and needs nothing installed.

The live app is at https://clauseanchor.icystone-c7631062.centralindia.azurecontainerapps.io/. It sleeps when nobody uses it, so the first visit after a quiet spell takes 1 to 3 minutes.

Do the steps in order. GitHub's and Azure's screens change now and then, so if a label here does not match, look for the closest one.

## Before you start

You need an Azure for Students subscription. Sign up at https://azure.microsoft.com/en-in/free/students/ and sign in with a personal Microsoft account, not your college one, so the subscription outlives your college address.

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
3. Click **Choose a tag**, type `model-v0`, and click **Create new tag: model-v0 on publish**. Leave the target as `main`. The tag is lowercase, because the workflow looks for exactly that name.
4. Set the title to `Model v0 (candidate prototype)`.
5. Write one line in the description box, such as `Model used by the live deployment. Not source code.`
6. Drag `clauseanchor-candidate-prototype-v0.zip` into the box at the bottom that says **Attach binaries by dropping them here or selecting them**. This is the assets area, not the description. Wait until the upload bar finishes and the file name shows with its size.
7. Tick **Set as a pre-release**. Untick **Set as the latest release** if it is ticked. Click **Publish release**.
8. Check that the release page lists the zip under **Assets**.

## 2. Build the image

1. Push every commit you want in the image to `main`. The run builds the latest commit on the branch you pick.
2. In the repository, open the **Actions** tab. If GitHub says workflows are disabled, click the button that enables them.
3. In the left list, click **image**. Click **Run workflow**, keep the branch as `main`, and click the green **Run workflow** button. Do not use **Re-run** on an old run. It rebuilds that run's old commit, not the latest one.
4. Open the new run and its job. The steps run in this order: download the model and check its hash, build the image, start the container, run the smoke test, check memory, publish. The run time was not recorded, and the workflow stops itself after 60 minutes.
5. A green tick means the image is published. Open the run's **Summary**. It has three lines: the image size, the peak memory, and a **Published** line that names both tags, `latest` and the full commit SHA. The first green run, on commit `c26236b`, reported an image of 1671 MiB and a container peak of 1026 MiB, file cache included.
6. A red cross means a step failed. Open that step and copy its last 50 lines. Read them before you run the workflow again.
7. Make the image public once, because Azure pulls it with no password. Open your GitHub profile, then the **Packages** tab, then **clauseanchor**, then **Package settings**. Under **Danger Zone**, click **Change visibility**, choose **Public**, type `clauseanchor` to confirm, and click the button. Public means anyone can download the image, and the model is inside it. Check with Tanishq that the model may be public before you do this. The package stays public for later builds.

## 3. One-time setup in Cloud Shell

1. Open Cloud Shell from the portal's top bar (the `>_` button) or at https://shell.azure.com, and choose **Bash**. If it asks you to create storage on first use, read the screen before you accept.
2. Add the Container Apps commands. Cloud Shell is ephemeral and may lose installed extensions between sessions, so run this again whenever `az containerapp` is not recognised:

   ```bash
   az extension add --name containerapp --upgrade
   ```

3. Register two services, once per subscription:

   ```bash
   az provider register --namespace Microsoft.App --wait
   az provider register --namespace Microsoft.OperationalInsights --wait
   ```

4. Check that both say `Registered`:

   ```bash
   az provider show --namespace Microsoft.App --query registrationState -o tsv
   az provider show --namespace Microsoft.OperationalInsights --query registrationState -o tsv
   ```

## 4. Create the app

The commands use the names `clauseanchor-rg` for the resource group, `clauseanchor-env` for the environment and `clauseanchor` for the app. A student subscription allows only some regions, and Central India worked here. An error that mentions a policy means the region is not allowed, so pick another allowed one and use it in both commands below and in the file's `location` line.

1. Create the resource group and the environment. `--logs-destination none` turns off Log Analytics, which bills past its free tier. The trade-off is that no log history is kept (step 8):

   ```bash
   az group create -n clauseanchor-rg -l centralindia
   az containerapp env create -n clauseanchor-env -g clauseanchor-rg --location centralindia --logs-destination none
   ```

   Azure reports this environment's mode as `Express`. Microsoft describes Express as an environment tier on Consumption billing (per-second vCPU and memory, scale to zero, no environment fee). It supports HTTP and TCP probes, HTTP scaling, single-revision rolling updates and live log streaming. It does not support custom KEDA scalers, multiple revisions or traffic splitting, HTTP/2, insecure HTTP, custom domains, session affinity, Easy Auth, sidecars or init containers. That comes from Microsoft's overview, read on 10 November 2026. Nothing here was measured against it.

2. Get the app's spec into Cloud Shell. It is the file `deploy/azure-containerapp.yaml` in this repository. Use the **Manage files**, **Upload** button in Cloud Shell's toolbar, or download it from GitHub:

   ```bash
   curl -O https://raw.githubusercontent.com/TheMEGALODON55681/clauseanchor/main/deploy/azure-containerapp.yaml
   ```

3. Fill in the environment's id. The file holds the placeholder `<ENV_ID>`:

   ```bash
   ENV_ID=$(az containerapp env show -n clauseanchor-env -g clauseanchor-rg --query id -o tsv)
   sed -i "s|<ENV_ID>|$ENV_ID|" azure-containerapp.yaml
   ```

   ```bash
   grep ENV_ID azure-containerapp.yaml
   ```

   The last command must print nothing. The filled file holds your subscription id, so keep it out of git.

4. The file's `image` line names the commit that was deployed first. To deploy a newer build instead, replace that tag with the build's full commit SHA (step 6 explains where to read it) before you create the app.
5. Create the app:

   ```bash
   az containerapp create -n clauseanchor -g clauseanchor-rg --yaml azure-containerapp.yaml
   ```

What the file sets: 2 vCPU and 4 Gi of memory, external HTTPS ingress to port 8000, one revision at a time, and 0 to 1 replicas with one HTTP scale rule at 10 concurrent requests. It sets a startup probe on `/api/v1/ready` (about 330 seconds for the image pull and the model load) and a liveness probe on `/api/v1/health`, and no readiness probe. The file's comments give the reasons.

Keep the maximum at 1. Sessions live in the memory of one replica, so a second copy could not find them.

## 5. Verify

1. Read the app's address:

   ```bash
   FQDN=$(az containerapp show -n clauseanchor -g clauseanchor-rg --query properties.configuration.ingress.fqdn -o tsv)
   echo "https://$FQDN"
   ```

2. Poll `/api/v1/ready` until it answers 200. The loop prints the status code about every 10 seconds and stops after about 6 minutes. A request to a sleeping app may print `000` while the app starts:

   ```bash
   for i in $(seq 1 12); do code=$(curl -s -o /dev/null --max-time 20 -w "%{http_code}" "https://$FQDN/api/v1/ready"); echo "$(date +%T) $code"; [ "$code" = "200" ] && break; sleep 10; done
   ```

3. Open the address in a browser. The first visit takes 1 to 3 minutes while Azure starts the container and loads the model, so wait and refresh if you see an error.
4. Work through the check below with a PDF and a Word file of your own, each under 10 MB. Use sample contracts, not confidential ones.

### The check

**1. Landing**

- [ ] The page loads and the browser console shows no red error.
- [ ] **Review a contract** opens the upload step. Under it, a note says the sample contract is not available in this build yet.
- [ ] Nothing on the page says a clause is a burden, a benefit or "favours you".

**2. Upload, PDF then Word**

- [ ] Choose the PDF. The page shows the file name, then the page count, and moves to a ready state.
- [ ] Choose the Word file in its place. The name changes, with no "most documents" error. (The first file is deleted on the server.)
- [ ] Next: step 2 shows a notice that this build does not use your side yet. Pick any role, then a party or "None of these", then Next.

**3. Categories and start**

- [ ] Step 3 lists the categories in seven groups. Start review is disabled with nothing chosen, and the hint says to choose at least one.
- [ ] Choose three CUAD categories (for example Governing Law, Parties, Non-Compete) and one from India-specific. The count reads 4 of 46.
- [ ] Below the picker, the switch reads "Review under Indian law" with the line "Adds the five India-specific categories. In this build they show as not yet available."
- [ ] Start review. The Reader opens and lists only those four categories.

**4. Progress and highlights**

- [ ] A band shows "Checking categories" (or "Waiting in the queue") and "N of M steps".
- [ ] When it ends, marks appear on the text and the sidebar shows counts. Select a mark: the panel shows the quoted wording and "Confidence not validated". It shows no burden or benefit label.
- [ ] The India category reads Unavailable.
- [ ] The text wraps to the column. PDF line breaks are not kept (expected).
- [ ] The toolbar button reads "Report not available yet" and is disabled. The Manual review row reads "not available yet".
- [ ] Open the role menu: it holds one disabled line.

**5. Cancel**

- [ ] Start a review with many categories (Select all) on a long file. While the band shows, press Cancel.
- [ ] The review stops, and the note says you stopped the review.

**6. File errors**

- [ ] A file over 10 MB (any large file renamed to `.pdf`): the upload area says "This file is larger than 10 MB." and nothing is sent.
- [ ] An unsupported type (a `.txt` or `.png`): "This file type is not supported. Upload a PDF or DOCX."

**7. Delete and the Expired page**

- [ ] In the Reader, Delete document, then confirm. The Expired page opens and says the contract was deleted.
- [ ] Type the app's address followed by `#/review/abc` after a reload: the Expired page opens.

**8. Pages that wait for Phase 3**

- [ ] `#/accuracy` shows its heading and a "not available in this build yet" state, with no table.
- [ ] `#/how-it-works` reads cleanly and says the Accuracy page and the manual review list are not available yet.

If something fails, go to "If something goes wrong" below and read the log stream (step 8) while you repeat the step.

## 6. Update after a code change

1. Push the change to `main`.
2. Run the workflow again (step 2). Do not re-run an old run.
3. Open the new run's **Summary** and read the **Published** line. It ends in the full 40-character commit SHA. Copy only that SHA. The line is there to read, not to paste.
4. In Cloud Shell, name that SHA as the tag:

   ```bash
   az containerapp update -n clauseanchor -g clauseanchor-rg --image ghcr.io/themegalodon55681/clauseanchor:<full commit SHA>
   ```

   For the build of commit `c26236b`, the command was:

   ```bash
   az containerapp update -n clauseanchor -g clauseanchor-rg --image ghcr.io/themegalodon55681/clauseanchor:c26236bae1587a1052f486b323ee62dd74708bf9
   ```

5. Use the SHA tag, never `:latest`. If the tag is the same string the app already runs, Azure may not start a new revision. That is reasoning, not a test.
6. If `az containerapp` is not recognised, Cloud Shell has lost its extension. Run `az extension add --name containerapp --upgrade` first.

An update makes a new revision and ends every session, so do not run one during a demo.

## 7. Demo day

A sleeping app has a cold start. To avoid one during a demo, keep one replica awake for the demo window only.

1. About 15 minutes before the demo, set the minimum to 1:

   ```bash
   az containerapp update -n clauseanchor -g clauseanchor-rg --min-replicas 1
   ```

2. Confirm that it took. The output must show `"minReplicas": 1`:

   ```bash
   az containerapp show -n clauseanchor -g clauseanchor-rg --query properties.template.scale
   ```

   Microsoft's overview of Express environments does not describe a minimum replica setting, so this step is unverified on this app. If the output still shows 0, or the command fails, the app may sleep during the demo.
3. Open the link once, so you know it is awake.
4. Straight after the demo, set the minimum back to 0 and run the confirm command again:

   ```bash
   az containerapp update -n clauseanchor -g clauseanchor-rg --min-replicas 0
   ```

Do not change any other setting during the demo, because a change ends every session.

**Cost warning.** A replica kept warm for a whole day uses 172,800 vCPU-seconds and 345,600 GiB-seconds, which is nearly the whole monthly free grant (step 9). Azure bills an idle replica at a lower rate, so those figures are an upper bound. Even so, never leave the minimum at 1.

## 8. Logs

Watch the container's output live:

```bash
az containerapp logs show -n clauseanchor -g clauseanchor-rg --follow --tail 50
```

This shows the console logs. Add `--type system` for platform events, such as a failed probe or an image pull:

```bash
az containerapp logs show -n clauseanchor -g clauseanchor-rg --type system --follow --tail 50
```

The environment was created with the logs destination set to none, so Azure stores no history. You can watch a log live and see nothing of what happened an hour ago. Microsoft's log options page says live streaming still works when storage is off. These commands have not been run on this app yet.

## 9. Cost and budget

The Consumption plan gives each subscription 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests free every calendar month. At 2 vCPU and 4 GiB, one running hour uses 7,200 vCPU-seconds and 14,400 GiB-seconds, so the grant covers about 25 active hours a month (180,000 / 2 / 3600, and 360,000 / 4 / 3600). Health-probe requests are not billable. When nobody uses the app, it scales to zero and uses nothing.

Anything over the grant comes out of your Azure for Students credit: USD 100 for 12 months, with no card. When the credit runs out or expires, Azure disables the subscription and its services. There is no card on file to charge. To see what is left, open https://www.microsoftazuresponsorships.com/balance, or open **Cost Management** in the portal.

A budget named `clauseanchor` is in place:

| Setting | Value |
|---|---|
| Scope | The Azure for Students subscription |
| Period | Monthly |
| Amount | ₹850, about USD 10 (the subscription bills in INR) |
| Alert | At 80 percent of actual cost, by email |
| Expires | 31 October 2028 |

To change it or add another, open **Cost Management**, then **Budgets**.

## 10. Sharing

The address is public, and anyone with it can upload a file. Tell visitors to use sample contracts, not confidential ones, and that the first visit after a quiet spell takes 1 to 3 minutes. The app deletes a document when the session ends, and a session lasts 60 minutes at most.

## If something goes wrong

| Problem | Fix |
|---|---|
| "Not registered to use namespace Microsoft.App" | Register the two services in step 3 |
| `az containerapp` is not recognised | Run `az extension add --name containerapp --upgrade` (step 3) |
| `/api/v1/ready` answers 503 | The model is still loading, or it failed to load. Read the log stream (step 8), then add `--type system`. The image build already checks the model bundle |
| The app keeps restarting | Open the system log (`--type system`) and look for failed probes. Check that memory is 4 Gi and the startup probe's failure threshold is 10: `az containerapp show -n clauseanchor -g clauseanchor-rg -o yaml` |
| "Unauthorized" or "manifest unknown" when Azure pulls the image | Make the package public (step 2.7) and check that the tag in the file or the update command is a full SHA that was published |
| An update changed nothing | `:latest`, or the tag that already runs, may start no new revision (reasoned, not tested). Use the full SHA from the new run's **Published** line (step 6). `az containerapp show -n clauseanchor -g clauseanchor-rg --query "properties.template.containers[0].image" -o tsv` prints the image the app runs now |
| The image build stops at the model bundle check | The message names the problem: a missing file or a digest that does not match. Read it, fix the model release or the build context, and run the workflow again |
| "Session expired" straight after a wait | Normal after the app has slept: sessions live in memory. Start a new review |
