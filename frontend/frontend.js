document.addEventListener('DOMContentLoaded', () => {
    const navItems = document.querySelectorAll('.nav-item');
    const mainContent = document.querySelector('.content');

    const API_BASE_URL = 'http://127.0.0.1:8000/api';
    const MAX_CATEGORY_LENGTH = 25;
    const MAX_TITLE_LENGTH = 20;
    const MAX_DESCRIPTION_LENGTH = 250;

    // Attempt to load saved session data on startup
    let accessToken = localStorage.getItem('accessToken') || null;
    let currentUsername = localStorage.getItem('currentUsername') || 'Guest';
    let currentUserId = null;

    // Helper to get authorization headers
    const getAuthHeaders = () => ({
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
    });

    const isSuccess = (status) => status >= 200 && status < 300;

    const isDueSoon = (task) => {
        if (task.status === 'completed' || !task.dueDate) {
            return false;
        }

        const dueDateTimeString = `${task.dueDate}T${task.dueTime || '00:00:00'}`;
        const dueTime = new Date(dueDateTimeString).getTime();
        const currentTime = Date.now();
        const difference = dueTime - currentTime;

        const oneDayInMs = 24 * 60 * 60 * 1000;

        return difference <= oneDayInMs;
    };

    const isTokenValid = (token) => {
        if (!token) return false;
        try {
            const payloadBase64 = token.split('.')[1];
            if (!payloadBase64) return false;

            const base64 = payloadBase64.replace(/-/g, '+').replace(/_/g, '/');
            const payload = JSON.parse(atob(base64));

            const expirationTimeMs = payload.exp * 1000;

            return expirationTimeMs > Date.now();

        } catch (e) {
            console.error("Failed to decode or validate token:", e);
            return false;
        }
    };

    const checkAndClearExpiredToken = () => {
        if (accessToken && !isTokenValid(accessToken)) {
            console.warn("Session token expired. Logging out user.");
            alert("Your session has expired. Please log in again.");
            logoutUser();
        }
    };


    const registerUser = async (name, email, password) => {
        try {
            const response = await axios.post(`${API_BASE_URL}/auth/register`, {
                name,
                email,
                password
            });
            return response.data;
        } catch (error) {
            console.error("Registration Error:", error.response);
            throw error.response;
        }
    };

    const loginUser = async (email, password) => {
        try {
            const loginData = { username: email, password: password };

            const response = await axios.post(`${API_BASE_URL}/auth/login`, loginData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
                },
                transformRequest: [(data, headers) => {
                    return Object.keys(data).map(key =>
                        encodeURIComponent(key) + '=' + encodeURIComponent(data[key])
                    ).join('&');
                }]
            });

            accessToken = response.data.access_token;
            currentUsername = email.split('@')[0];
            localStorage.setItem('accessToken', accessToken);
            localStorage.setItem('currentUsername', currentUsername);

            return response.data;

        } catch (error) {
            console.error("Login Error:", error.response);
            throw error.response;
        }
    };

    const logoutUser = () => {
        accessToken = null;
        currentUsername = 'Guest';
        localStorage.removeItem('accessToken');
        localStorage.removeItem('currentUsername');
        currentUserId = null;
    };


    const fetchTasks = async () => {
        if (!accessToken) throw new Error("User not authenticated.");
        try {
            const response = await axios.get(`${API_BASE_URL}/tasks/`, {
                headers: getAuthHeaders()
            });
            return response.data;
        } catch (error) {
            console.error("Fetch Tasks Error:", error.response);

            if (error.response && error.response.status === 401) {
                alert("Session expired or invalid token. Logging out.");
                logoutUser();
                await reloadCurrentPage('home');
            }

            throw error.response?.data?.detail || "Failed to fetch tasks.";
        }
    };

    const createTask = async (taskData) => {
        if (!accessToken) throw new Error("User not authenticated.");
        try {
            const response = await axios.post(`${API_BASE_URL}/tasks/`, taskData, {
                headers: getAuthHeaders()
            });
            return response.data;
        } catch (error) {
            console.error("Create Task Error:", error.response);
            throw error.response?.data?.detail || "Failed to create task.";
        }
    };

    const updateTask = async (taskId, taskData) => {
        if (!accessToken) throw new Error("User not authenticated.");
        try {
            const response = await axios.put(`${API_BASE_URL}/tasks/${taskId}`, taskData, {
                headers: getAuthHeaders()
            });
            return response.data;
        } catch (error) {
            console.error("Update Task Error:", error.response);
            throw error.response?.data?.detail || "Failed to update task.";
        }
    };

    const deleteTask = async (taskId) => {
        if (!accessToken) throw new Error("User not authenticated.");
        try {
            const response = await axios.delete(`${API_BASE_URL}/tasks/${taskId}`, {
                headers: getAuthHeaders()
            });
            return isSuccess(response.status);
        } catch (error) {
            console.error("Delete Task Error:", error.response);
            throw error.response?.data?.detail || "Failed to delete task.";
        }
    };

    const fetchTaskStats = async () => {
        if (!accessToken) throw new Error("User not authenticated.");
        try {
            const response = await axios.get(`${API_BASE_URL}/tasks/stats`, {
                headers: getAuthHeaders()
            });
            return response.data;
        } catch (error) {
            console.error("Fetch Stats Error:", error.response);
            throw error.response?.data?.detail || "Failed to fetch statistics.";
        }
    };

    let cachedTasks = [];

    const getCategoryOptionsHtml = (tasks) => {
        const uniqueCategories = new Set(tasks.map(t => t.category).filter(cat => cat && cat.trim() !== ''));

        return Array.from(uniqueCategories).map(cat =>
            `<option value="${cat}">`
        ).join('');
    };

    const getTaskFormHtml = () => {
        const categoryOptions = getCategoryOptionsHtml(cachedTasks);

        return `
            <form id="new-task-form-on-card" class="task-creation-form">
                <div class="form-group-card">
                    <input type="text" id="task-title" required minlength="3" placeholder="Task Title (min 3 chars)">
                </div>
                <div class="form-group-card">
                    <textarea id="task-description" placeholder="Description..."></textarea>
                </div>
                <div class="form-group-card form-group-date-time">
                    <label>Due:</label>
                    <input type="date" id="task-date"> 
                    <input type="time" id="task-time"> 
                </div>
                
                <div class="form-group-card form-group-category">
                    <input list="category-list" id="task-category" name="task-category" placeholder="Select or type Category (Optional)">
                    <datalist id="category-list">
                        ${categoryOptions}
                    </datalist>
                </div>
                
                <div class="card-footer-form compact-buttons">
                    <button type="submit" class="submit-btn save-button compact-btn" title="Save">
                        <i class="fas fa-check"></i> Save
                    </button>
                    <button type="button" class="submit-btn cancel-button compact-btn" id="cancel-add-task-on-card" title="Cancel">
                        <i class="fas fa-times"></i> Cancel
                    </button>
                </div>
            </form>
        `;
    };


    const renderTaskCard = (task) => {
        let color, statusText;
        let alertClass = '';
        let iconHtml = '';

        if (task.status === 'completed') {
            color = 'green';
            statusText = 'Completed';

        } else if (isDueSoon(task)) {
            alertClass = ' alert-card';
            color = 'red';
            statusText = 'Due Soon'; 
            iconHtml = `<i class="fas fa-exclamation-triangle card-alert-icon"></i>`;

        } else if (task.status === 'in-progress') {
            color = 'orange';
            statusText = 'In Progress';


        } else {
            color = 'purple';
            statusText = 'Not Started';
        }

        if (iconHtml === '' && task.status !== 'completed') {
            iconHtml = task.icon ? `<i class="fas ${task.icon} card-alert-icon"></i>` : '';
        }

        const dueDateDisplay = task.dueDate || '';
        const timeDisplay = task.dueTime ? task.dueTime.substring(0, 5) : '';

        const dueDateHtml = dueDateDisplay ? `<span class="due-date">${dueDateDisplay} <br> ${timeDisplay}</span>` : '';


        let buttonHtml;
        if (task.status === 'in-progress') {
            buttonHtml = `<button class="completed-button" data-id="${task.id}" title="Mark as Completed"><i class="fas fa-check"></i></button>`;
        } else if (task.status === 'pending' || task.status === 'not started') {
            buttonHtml = `<button class="start-button" data-id="${task.id}" title="Start Task">Start</button>`;
        } else {
            buttonHtml = `<button class="completed-button disabled" disabled>Completed</button>`;
        }


        return `
            <div class="task-card ${color}-card${alertClass}" data-id="${task.id}" data-status="${task.status}">
                <div class="card-header">
                    <h3>${task.title}</h3>
                    ${dueDateHtml}
                </div>
                <p class="card-description">${task.description || 'No description provided.'}</p>
                <div class="card-footer">
                    <span class="card-category">Category: ${task.category || 'Uncategorized'}</span>
                    ${buttonHtml}
                </div>
                ${iconHtml}
            </div>
        `;
    };

    const getInlineEditFormHtml = (task) => {
        const uniqueCategories = new Set(cachedTasks.map(t => t.category).filter(cat => cat && cat.trim() !== ''));
        const categoryOptions = Array.from(uniqueCategories).map(cat =>
            `<option value="${cat}" ${task.category === cat ? 'selected' : ''}>${cat}</option>`
        ).join('');

        const statusOptions = ['pending', 'in-progress', 'completed'].map(status => {
            let displayStatus = status.charAt(0).toUpperCase() + status.slice(1).replace('-', ' ');
            if (status === 'pending') displayStatus = 'Not Started';

            return `<option value="${status}" ${task.status === status ? 'selected' : ''}>${displayStatus}</option>`;
        }).join('');

        const formattedDate = task.dueDate || '';
        const formattedTime = task.dueTime ? task.dueTime.substring(0, 5) : '';

        return `
            <div class="task-edit-container">
                <form id="task-edit-form-${task.id}" class="task-edit-form">
                    <div class="form-fields">
                        <div class="form-group">
                            <label for="edit-title-${task.id}">Title</label>
                            <input type="text" id="edit-title-${task.id}" value="${task.title}" required minlength="3">
                        </div>
                        <div class="form-group">
                            <label for="edit-description-${task.id}">Description</label>
                            <textarea id="edit-description-${task.id}">${task.description || ''}</textarea>
                        </div>

                        <div class="date-time-inputs">
                            <div class="form-group">
                                <label for="edit-date-${task.id}">Due Date</label>
                                <input type="date" id="edit-date-${task.id}" value="${formattedDate}">
                            </div>
                            <div class="form-group">
                                <label for="edit-time-${task.id}">Time</label>
                                <input type="time" id="edit-time-${task.id}" value="${formattedTime}">
                            </div>
                        </div>

                        <div class="category-status-inputs">
                            <div class="form-group">
                                <label for="edit-category-${task.id}">Category</label>
                                <input list="category-list-${task.id}" id="edit-category-${task.id}" name="task-category" placeholder="Select or type Category" value="${task.category || ''}">
                                <datalist id="category-list-${task.id}">
                                    ${categoryOptions}
                                </datalist>
                            </div>
                            <div class="form-group">
                                <label for="edit-status-${task.id}">Status</label>
                                <select id="edit-status-${task.id}" required>
                                    ${statusOptions}
                                </select>
                            </div>
                        </div>
                    </div>

                    <div class="task-actions edit-actions">
                        <button type="button" class="list-edit-btn compact-btn cancel-edit-btn" data-id="${task.id}" title="Cancel Edit">
                            <i class="fas fa-times"></i> Cancel
                        </button>
                        <button type="submit" class="list-edit-btn compact-btn save-edit-btn" data-id="${task.id}" title="Save Changes">
                            <i class="fas fa-save"></i> Save
                        </button>
                    </div>
                </form>
            </div>
        `;
    };


    const getDashboardContent = async () => {
        if (!accessToken) return `<div class="info-message">Please log in to see your dashboard.</div>`;

        let tasks;
        try {
            tasks = await fetchTasks();
            cachedTasks = tasks;
        } catch (error) {
            return `<div class="error-message">Error loading tasks: ${error}</div>`;
        }

        let taskCardsHtml;
        if (tasks.length === 0) {
            taskCardsHtml = `<p style="text-align: center; margin-top: 30px; color: var(--primary-color);">No tasks found. Click "Add New Task" to begin.</p>`;
        } else {
            taskCardsHtml = tasks.map(renderTaskCard).join(''); // 'tasks' dizisini kullan (pendingTasks değil)
        }

        const uniqueCategories = [...new Set(tasks.map(t => t.category || 'Uncategorized'))];
        const categoryOptions = uniqueCategories.map(cat => `<option value="${cat}">${cat}</option>`).join('');


        return `
            <div class="dashboard-header">
                <h2 class="dashboard-title">Dashboard</h2>
                <div class="filters">
                    <div class="filter-group">
                        <label for="category">Category</label>
                        <select id="category">
                            <option value="all">-------------</option>
                            ${categoryOptions}
                        </select>
                        <i class="fas fa-caret-down"></i>
                    </div>
                    <div class="filter-group">
                        <label for="status">Status</label>
                        <select id="status">
                            <option value="all">-------------</option>
                            <option value="pending">Not Started</option>
                            <option value="in-progress">In Progress</option>
                            <option value="completed">Completed</option>
                        </select>
                        <i class="fas fa-caret-down"></i>
                    </div>
                </div>
            </div>
            
            <div class="task-grid" id="task-grid">
                ${taskCardsHtml}

                <div class="task-card empty-card" data-action="add-task"> 
                    <button class="add-button">
                        <i class="fas fa-plus"></i> Add New Task
                    </button>
                </div>
            </div>
        `;
    };


    const renderTaskRow = (task) => {
        let colorClass;
        let statusText;
        let alertIcon = '';

        if (task.status === 'completed') {
            colorClass = 'green-card';
            statusText = 'Completed';
        } else if (task.status === 'in-progress') {
            colorClass = 'orange-card';
            statusText = 'In Progress';
        } else {
            colorClass = 'purple-card';
            statusText = 'Not Started';
        }

        if (isDueSoon(task)) {
            alertIcon = `<i class="fas fa-exclamation-triangle list-alert-icon"></i>`;
        }

        const displayDate = task.dueDate || 'N/A';
        const displayTime = task.dueTime ? task.dueTime.substring(0, 5) : 'N/A';
        const itemCategory = task.category ? task.category.toLowerCase().replace(/\s/g, '-') : 'uncategorized';


        return `
            <div class="task-list-item ${colorClass}" data-id="${task.id}" data-status="${task.status}" data-category="${itemCategory}" data-title="${task.title}">
                <div class="task-details">
                    <h3 class="task-title">${task.title} ${alertIcon}</h3>
                    <p class="task-description">${task.description || 'No description provided.'}</p>
                    <div class="task-date-info">
                        <span class="date-label">Due Date: ${displayDate}</span>
                        <span class="time-label">Time: ${displayTime}</span>
                    </div>
                </div>
                
                <div class="task-management">
                    <div class="task-meta">
                        <span class="category-info">Category: ${task.category || 'Uncategorized'}</span>
                        <span class="status-info">Status: ${statusText}</span>
                    </div>

                    <div class="task-actions">
                        <button class="delete-btn list-delete-btn" data-id="${task.id}">Delete</button>
                        <button class="edit-btn list-edit-btn" data-id="${task.id}">Edit</button>
                        </div>
                </div>
            </div>
        `;
    };


    const getTasksContent = async () => {
        if (!accessToken) return `<div class="info-message">Please log in to see your tasks list.</div>`;

        let tasks;
        try {
            tasks = await fetchTasks();
            cachedTasks = tasks;
        } catch (error) {
            return `<div class="error-message">Error loading tasks: ${error}</div>`;
        }

        const uniqueCategories = [...new Set(tasks.map(t => t.category))].filter(Boolean);
        const categoryOptions = uniqueCategories.map(cat => `<option value="${cat.toLowerCase().replace(/\s/g, '-')}">${cat}</option>`).join('');

        const taskListHtml = tasks.map(renderTaskRow).join('');


        return `
            <div class="tasks-container">
                <div class="dashboard-header">
                    <h2 class="dashboard-title">Tasks</h2>
                    <div class="filters">
                        <div class="filter-group">
                            <label for="category-filter">Category</label>
                            <select id="category-filter">
                                <option value="all">-------------</option>
                                ${categoryOptions}
                            </select>
                            <i class="fas fa-caret-down"></i>
                        </div>
                        <div class="filter-group">
                            <label for="status-filter">Status</label>
                            <select id="status-filter">
                                <option value="all">-------------</option>
                                <option value="pending">Not Started</option>
                                <option value="in-progress">In Progress</option>
                                <option value="completed">Completed</option>
                            </select>
                            <i class="fas fa-caret-down"></i>
                        </div>
                    </div>
                </div>
                
                <div class="task-list" id="task-list">
                    ${taskListHtml || '<p style="text-align: center; color: var(--primary-color);">No tasks found. Use the input field above to quickly add one.</p>'}
                </div>
            </div>
        `;
    };


    const getLoginRegisterContent = () => {
        return `
            <div class="auth-container">
                <div class="auth-box">
                    <div class="auth-switch">
                        <button class="switch-btn active" data-form="login">Login</button>
                        <button class="switch-btn" data-form="register">Register</button>
                    </div>

                    <form class="auth-form login-form active">
                        <h2>Login</h2>
                        <div class="form-group">
                            <label for="login-email">E-Mail</label>
                            <input type="email" id="login-email" required>
                        </div>
                        <div class="form-group">
                            <label for="login-password">Password</label>
                            <input type="password" id="login-password" required>
                        </div>
                        <button type="submit" class="submit-btn login-submit">Login</button>
                    </form>

                    <form class="auth-form register-form hidden">
                        <h2>Register</h2>
                        <div class="form-group">
                            <label for="register-username">Username</label>
                            <input type="text" id="register-username" required>
                        </div>
                        <div class="form-group">
                            <label for="register-email">E-Mail</label>
                            <input type="email" id="register-email" required>
                        </div>
                        <div class="form-group">
                            <label for="register-password">Password</label>
                            <input type="password" id="register-password" required>
                        </div>
                        <button type="submit" class="submit-btn register-submit">Register</button>
                    </form>
                </div>
            </div>
        `;
    };


    const getStatisticsContent = async () => {
        if (!accessToken) return `<div class="info-message">Please log in to see statistics.</div>`;

        let stats;
        try {
            stats = await fetchTaskStats();
        } catch (error) {
            return `<div class="error-message">Error loading statistics: ${error}</div>`;
        }

        if (Object.keys(stats).length === 0) {
            return `<div class="info-message" style="margin-top: 30px; color: var(--primary-color);">No task data available to generate statistics. Create some tasks first!</div>`;
        }

        setTimeout(() => setupStatisticsInteractions(stats), 0);

        return `
            <div class="statistics-container">
                <div class="dashboard-header">
                    <h2 class="dashboard-title">Task Statistics</h2>
                    <div class="filters">
                        <div class="filter-group">
                            <label for="group-by-filter">Group By</label>
                            <select id="group-by-filter">
                                <option value="category">Category</option>
                                <option value="status">Overall Status</option>
                            </select>
                            <i class="fas fa-caret-down"></i>
                        </div>
                    </div>
                </div>

                <div class="chart-area">
                    <canvas id="task-chart"></canvas>
                </div>
                
                <div id="chart-legend" class="chart-legend"></div>
            </div>
        `;
    };

    const statusColors = {
        'pending': 'rgba(150, 90, 250, 0.7)',
        'in-progress': 'rgba(255, 165, 0, 0.7)',
        'completed': 'rgba(60, 179, 113, 0.7)'
    };




    let taskChartInstance = null;

    const formatStatsForChart = (apiStats) => {
        const categories = Object.keys(apiStats).sort();
        const completedData = [];
        const incompleteData = [];

        categories.forEach(cat => {
            completedData.push(apiStats[cat].completed);
            incompleteData.push(apiStats[cat].incomplete);
        });

        return {
            labels: categories,
            datasets: [
                {
                    label: 'Completed',
                    data: completedData,
                    backgroundColor: statusColors['completed'],
                    borderColor: statusColors['completed'].replace('0.7', '1'),
                    borderWidth: 1
                },
                {
                    label: 'Incomplete (Pending/In Progress)',
                    data: incompleteData,
                    backgroundColor: statusColors['pending'],
                    borderColor: statusColors['pending'].replace('0.7', '1'),
                    borderWidth: 1
                }
            ]
        };
    };

    const renderTaskChart = (chartData) => {
        const ctx = document.getElementById('task-chart');

        if (!ctx) return;

        if (taskChartInstance) {
            taskChartInstance.destroy();
        }

        taskChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: chartData.datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Task Categories'
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Tasks'
                        },
                        ticks: {
                            precision: 0,
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true
                    },
                    title: {
                        display: true,
                        text: `Task Breakdown by Category and Status`
                    }
                }
            }
        });
    };

    const setupStatisticsInteractions = (stats) => {
        const chartData = formatStatsForChart(stats);
        renderTaskChart(chartData);
        const filterGroup = document.querySelector('.statistics-container .filters');
        if (filterGroup) {
            filterGroup.style.display = 'none';
        }
    };



    const reloadCurrentPage = async (page) => {
        const activeItem = document.querySelector(`.nav-item[data-page="${page}"]`);
        if (activeItem) {
            navItems.forEach(i => i.classList.remove('active'));
            activeItem.classList.add('active');
        }

        mainContent.innerHTML = `<div style="text-align: center; padding: 50px; color: var(--primary-color);">Loading ${page.toUpperCase()}...</div>`;

        await loadContent(page);
    };


    const setupAddTaskInteractionsOnCard = (cardElement) => {
        const form = document.getElementById('new-task-form-on-card');
        const cancelButton = document.getElementById('cancel-add-task-on-card');

        const resetCard = async () => {
            await reloadCurrentPage('home');
        };

        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const title = document.getElementById('task-title').value.trim();
                const description = document.getElementById('task-description').value.trim();
                const dueDate = document.getElementById('task-date').value.trim();
                const dueTime = document.getElementById('task-time').value.trim();
                const category = document.getElementById('task-category').value.trim() || null;

                if (category && category.length > MAX_CATEGORY_LENGTH) {
                    alert(`Category name is too long. Must be ${MAX_CATEGORY_LENGTH} characters or less.`);
                    return;
                }
                if (!title || title.length < 3) {
                    alert('Task title must be at least 3 characters long.');
                    return;
                }

                if (title.length > MAX_TITLE_LENGTH) {
                    alert(`Title is too long. Max ${MAX_TITLE_LENGTH} characters.`);
                    return;
                }

                if (description && description.length > MAX_DESCRIPTION_LENGTH) {
                    alert(`Description is too long. Max ${MAX_DESCRIPTION_LENGTH} characters.`);
                    return;
                }

                const newTaskData = {
                    title: title,
                    description: description || null,
                    category: category,
                    status: 'pending',
                    dueDate: dueDate || null,
                    dueTime: (dueTime ? dueTime + ":00" : null)
                };

                try {
                    await createTask(newTaskData);
                    alert(`Task "${title}" created successfully!`);
                    await resetCard();
                } catch (error) {
                    alert(`ERROR: Failed to create task. Details: ${error}`);
                }
            });
        }

        if (cancelButton) {
            cancelButton.addEventListener('click', resetCard);
        }
    };

    const setupDashboardInteractions = () => {
        const categorySelect = document.getElementById('category');
        const statusSelect = document.getElementById('status');
        const addTaskCard = document.querySelector('[data-action="add-task"]');
        const taskGrid = document.getElementById('task-grid');

        if (!categorySelect || !statusSelect || !addTaskCard || !taskGrid) {
            console.warn("Dashboard elements not found for interaction setup. Waiting for next load.");
            return;
        }

        const applyDashboardFilters = () => {
            const selectedCategory = categorySelect.value;
            const selectedStatus = statusSelect.value;
            const taskCards = taskGrid.querySelectorAll('.task-card:not(.empty-card)');

            taskCards.forEach(card => {
                const itemCategory = card.querySelector('.card-category').textContent.replace('Category: ', '').trim();
                const itemStatus = card.getAttribute('data-status');

                const categoryMatch = selectedCategory === 'all' || itemCategory === selectedCategory;
                const statusMatch = (selectedStatus === 'all' && itemStatus !== 'completed') || itemStatus === selectedStatus;

                if (categoryMatch && statusMatch) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        };

        if (categorySelect) categorySelect.addEventListener('change', applyDashboardFilters);
        if (statusSelect) statusSelect.addEventListener('change', applyDashboardFilters);

        if (addTaskCard) {
            const addCardClickListener = function () {
                if (document.querySelector('.task-creation-form')) return;
                addTaskCard.classList.remove('empty-card');
                addTaskCard.classList.add('primary-card', 'active-form');
                addTaskCard.setAttribute('data-action', 'add-task-active');
                addTaskCard.innerHTML = getTaskFormHtml();
                setupAddTaskInteractionsOnCard(addTaskCard);
                addTaskCard.removeEventListener('click', addCardClickListener);
            };
            addTaskCard.addEventListener('click', addCardClickListener);
        }

        taskGrid.addEventListener('click', async (e) => {
            const target = e.target.closest('button');
            if (!target || !target.dataset.id) return;

            const taskId = parseInt(target.dataset.id);
            let newStatus;

            if (target.classList.contains('start-button')) {
                newStatus = 'in-progress';
            } else if (target.classList.contains('completed-button') && !target.disabled) {
                newStatus = 'completed';
            } else {
                return;
            }

            const taskToUpdate = cachedTasks.find(t => t.id === taskId);
            if (!taskToUpdate) return alert("Task not found locally.");

            const updatePayload = {
                title: taskToUpdate.title,
                description: taskToUpdate.description,
                category: taskToUpdate.category,
                dueDate: taskToUpdate.dueDate,
                dueTime: taskToUpdate.dueTime,
                status: newStatus
            };

            try {
                await updateTask(taskId, updatePayload);
                alert(`Task status updated to: ${newStatus.toUpperCase()}`);
                await reloadCurrentPage('home');
            } catch (error) {
                alert(`ERROR: Failed to update task status. Details: ${error}`);
            }
        });
        applyDashboardFilters();
    };


    const setupTasksInteractions = () => {
        const listContainer = document.getElementById('task-list');
        const categoryFilter = document.getElementById('category-filter');
        const statusFilter = document.getElementById('status-filter');
        const addTaskBtn = document.getElementById('add-task-list-btn');

        if (!listContainer || !categoryFilter || !statusFilter) {
            console.warn("Tasks elements not found for interaction setup. Waiting for next load.");
            return;
        }

        const applyFilters = () => {
            const selectedCategory = categoryFilter.value;
            const selectedStatus = statusFilter.value;

            const taskItems = listContainer.querySelectorAll('.task-list-item');

            taskItems.forEach(item => {
                const itemCategory = item.getAttribute('data-category');
                const itemStatus = item.getAttribute('data-status');

                const categoryMatch = selectedCategory === 'all' || itemCategory === selectedCategory;
                const statusMatch = selectedStatus === 'all' || itemStatus === selectedStatus;

                if (categoryMatch && statusMatch) {
                    item.style.display = 'grid';
                } else {
                    item.style.display = 'none';
                }
            });
        };

        if (categoryFilter) categoryFilter.addEventListener('change', applyFilters);
        if (statusFilter) statusFilter.addEventListener('change', applyFilters);




        const findTask = (id) => cachedTasks.find(t => t.id === id);

        const handleDeleteTask = async (id) => {
            const taskToDelete = findTask(id);
            if (!taskToDelete) {
                alert("Error: Task not found in cache.");
                return;
            }

            if (confirm(`Are you sure you want to delete this task?\n\n"${taskToDelete.title}"`)) {
                try {
                    await deleteTask(id);

                    const taskElement = document.querySelector(`.task-list-item[data-id="${id}"]`);
                    if (taskElement) {
                        taskElement.remove();
                    }
                    cachedTasks = cachedTasks.filter(task => task.id !== id);

                    alert(`Task "${taskToDelete.title}" deleted.`);
                } catch (error) {
                    alert(`ERROR: Failed to delete task. Details: ${error}`);
                    await reloadCurrentPage('tasks');
                }
            }
        };

        const handleEditTask = (id) => {
            const task = findTask(id);
            const taskItem = document.querySelector(`.task-list-item[data-id="${id}"]`);

            if (taskItem.classList.contains('editing')) return;

            if (task && taskItem) {
                taskItem.setAttribute('data-original-html', taskItem.innerHTML);

                taskItem.classList.add('editing');
                taskItem.innerHTML = getInlineEditFormHtml(task);

                const form = document.getElementById(`task-edit-form-${id}`);
                const originalTaskHtml = taskItem.getAttribute('data-original-html');

                form.addEventListener('submit', async (e) => {
                    e.preventDefault();

                    const newTitle = document.getElementById(`edit-title-${id}`).value.trim();
                    const newDescription = document.getElementById(`edit-description-${id}`).value.trim();
                    const newDate = document.getElementById(`edit-date-${id}`).value.trim();
                    const newTime = document.getElementById(`edit-time-${id}`).value.trim();
                    const newCategory = document.getElementById(`edit-category-${id}`).value.trim() || null;
                    const newStatus = document.getElementById(`edit-status-${id}`).value.trim();

                    if (newCategory && newCategory.length > MAX_CATEGORY_LENGTH) {
                        alert(`Category name is too long. Must be ${MAX_CATEGORY_LENGTH} characters or less.`);
                        return;
                    }

                    if (newTitle.length < 3) {
                        alert('Title must be at least 3 characters.');
                        return;
                    }

                    if (newTitle.length > MAX_TITLE_LENGTH) {
                        alert(`Title is too long. Max ${MAX_TITLE_LENGTH} characters.`);
                        return;
                    }

                    if (newDescription && newDescription.length > MAX_DESCRIPTION_LENGTH) {
                        alert(`Description is too long. Max ${MAX_DESCRIPTION_LENGTH} characters.`);
                        return;
                    }
                    const updatePayload = {
                        title: newTitle,
                        description: newDescription || null,
                        category: newCategory,
                        status: newStatus,
                        dueDate: newDate || null,
                        dueTime: (newTime ? newTime + ":00" : null)
                    };

                    try {
                        await updateTask(id, updatePayload);
                        alert(`Task "${newTitle}" successfully updated.`);
                        await reloadCurrentPage('tasks');
                    } catch (error) {
                        alert(`ERROR: Failed to update task. Details: ${error}`);
                    }
                });

                const cancelButton = form.querySelector('.cancel-edit-btn');
                cancelButton.addEventListener('click', async () => {
                    taskItem.classList.remove('editing');
                    await reloadCurrentPage('tasks');
                });
            }
        };

        listContainer.addEventListener('click', (e) => {
            const target = e.target.closest('button');

            if (!target) return;

            const taskId = parseInt(target.getAttribute('data-id'));

            if (target.classList.contains('list-delete-btn')) {
                handleDeleteTask(taskId);
            } else if (target.classList.contains('list-edit-btn') && !target.classList.contains('save-edit-btn') && !target.classList.contains('cancel-edit-btn')) {
                handleEditTask(taskId);
            }
        });
    };


    const setupAuthInteractions = () => {
        const switchButtons = document.querySelectorAll('.auth-switch .switch-btn');
        const authForms = document.querySelectorAll('.auth-form');

        switchButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetForm = button.getAttribute('data-form');
                switchButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                authForms.forEach(form => {
                    const isTarget = form.classList.contains(`${targetForm}-form`);
                    if (isTarget) {
                        form.classList.remove('hidden');
                        form.classList.add('active');
                    } else {
                        form.classList.add('hidden');
                        form.classList.remove('active');
                    }
                });
            });
        });

        authForms.forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                if (form.classList.contains('login-form')) {
                    const emailValue = document.getElementById('login-email').value.trim();
                    const passwordValue = document.getElementById('login-password').value.trim();

                    if (!emailValue || !passwordValue) {
                        alert("Please enter both email and password.");
                        return;
                    }

                    try {
                        await loginUser(emailValue, passwordValue);
                        alert(`Logged in successfully, ${currentUsername}!`);

                        await reloadCurrentPage('home');

                    } catch (error) {
                        const errorDetail = error.data?.detail || "Login failed due to unknown error.";
                        alert(`Login Failed: ${errorDetail}`);
                        console.error('Login Error:', error);
                    }


                } else {
                    const nameInput = document.getElementById('register-username').value.trim();
                    const emailInput = document.getElementById('register-email').value.trim();
                    const passwordInput = document.getElementById('register-password').value.trim();

                    if (!nameInput || !emailInput || !passwordInput) {
                        alert("Please fill in all registration fields.");
                        return;
                    }

                    try {
                        await registerUser(nameInput, emailInput, passwordInput);
                        alert(`Registration succeeded! You can now log in.`);
                        document.querySelector('.switch-btn[data-form="login"]').click();
                    } catch (error) {
                        const errorDetail = error.data?.detail || "Registration failed due to unknown error.";
                        alert(`Registration Failed: ${errorDetail}`);
                        console.error('Registration Error:', error);
                    }
                }
            });
        });
    };

    const loadContent = async (pageName) => {

        if (pageName === 'home') {
            mainContent.innerHTML = await getDashboardContent();
            setupDashboardInteractions();
        } else if (pageName === 'tasks') {
            mainContent.innerHTML = await getTasksContent();
            setupTasksInteractions();
        } else if (pageName === 'stats') {
            mainContent.innerHTML = await getStatisticsContent();
        }
        else {
            mainContent.innerHTML = `
            <h2>${pageName.charAt(0).toUpperCase() + pageName.slice(1)} Page</h2>
            <p>Content for the ${pageName} page.</p>
        `;
        }
    };


    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();

            const pageName = item.getAttribute('data-page');

            if (pageName === 'logout') {
                const isConfirmed = confirm('Are you sure you want to log out?');

                if (isConfirmed) {
                    logoutUser();
                    navItems.forEach(i => i.classList.remove('active'));
                    document.querySelector('[data-page="home"]').classList.add('active');
                    mainContent.innerHTML = getLoginRegisterContent();
                    setupAuthInteractions();
                    alert("You have been logged out.");
                } else {
                }

            } else {
                navItems.forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                if (!accessToken && pageName !== 'home') {
                    mainContent.innerHTML = getLoginRegisterContent();
                    setupAuthInteractions();
                    document.querySelector('[data-page="home"]').classList.add('active');
                } else {
                    loadContent(pageName);
                }
            }
        });
    });


    checkAndClearExpiredToken();

    if (!accessToken) {
        document.querySelector('[data-page="home"]').classList.add('active');
        mainContent.innerHTML = getLoginRegisterContent();
        setupAuthInteractions();
    } else {
        document.querySelector('[data-page="home"]').classList.add('active');
        loadContent('home');
    }
});
