document.addEventListener("DOMContentLoaded", () => {
    const feed = document.getElementById("log-feed");
    const statTotal = document.getElementById("stat-total");
    const statBlocked = document.getElementById("stat-blocked");

    // Track what we've already rendered to avoid full rebuilds
    let knownLogTimestamps = new Set();

    async function pollLogs() {
        try {
            const response = await fetch("/api/logs");
            const data = await response.json();

            if (data.logs) {
                updateDashboard(data.logs);
            }
        } catch (error) {
            console.error("Failed to poll gateway logs:", error);
        }
    }

    function updateDashboard(logs) {
        // Update Stats
        statTotal.textContent = logs.length;
        const blockedCount = logs.filter(log => !log.security_passed).length;
        statBlocked.textContent = blockedCount;

        // Render zero state
        if (logs.length === 0) {
            feed.innerHTML = `<div class="loading" style="animation: none; opacity: 0.5;">Awaiting Agent Data...</div>`;
            return;
        }

        // On first real load, clear loading text
        if (feed.querySelector(".loading")) {
            feed.innerHTML = "";
        }

        // Render new logs (we get them newest first from the API)
        logs.forEach((log) => {
            // Use timestamp as unique ID
            if (!knownLogTimestamps.has(log.timestamp)) {
                const card = createLogCard(log);

                // Prepend since the API sends newest first but we want them at the top
                feed.appendChild(card);
                knownLogTimestamps.add(log.timestamp);
            }
        });
    }

    function createLogCard(log) {
        const div = document.createElement("div");
        div.className = "log-card";

        const isPassed = log.security_passed;
        const badgeClass = isPassed ? "passed" : "blocked";
        const badgeText = isPassed ? "Passed" : "Blocked";
        const reasonClass = isPassed ? "passed-text" : "blocked-text";
        const icon = isPassed ? "✓" : "✗";

        // Format the date nicely
        const date = new Date(log.timestamp);
        const timeString = date.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
            + '.' + date.getMilliseconds().toString().padStart(3, '0');

        // Pretty print the JSON arguments
        let formattedArgs = log.arguments;
        try {
            const parsed = typeof log.arguments === 'string' ? JSON.parse(log.arguments) : log.arguments;
            formattedArgs = JSON.stringify(parsed, null, 2);
        } catch (e) { }

        div.innerHTML = `
            <div class="log-card-header">
                <div>
                    <span class="tool-name">${log.tool}</span>
                    <span class="time" style="margin-left: 10px">${timeString}</span>
                </div>
                <span class="badge ${badgeClass}">${badgeText}</span>
            </div>
            <div class="payload">${formattedArgs.replace(/\n/g, '<br>').replace(/ /g, '&nbsp;')}</div>
            <div class="reason ${reasonClass}">
                <span style="font-weight: bold;">${icon}</span> ${log.reason}
            </div>
        `;

        return div;
    }

    // Start Polling loop every 2 seconds
    setInterval(pollLogs, 2000);
    pollLogs(); // Initial fetch
});
