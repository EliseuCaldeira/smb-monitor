/*
 * This is the file where the main function resides.
 */

// UI elements:
const share_host	= document.getElementById('share_host')
const share_host_loading= document.getElementById('share_host_loading')
const share_name	= document.getElementById('share_name')
//const share_name_info	= document.getElementById('share_name_info')
const time_span		= document.getElementById('time_span')
const user_search	= document.getElementById('user_search')
const time_order_btn	= document.getElementById('time_order_btn')
const time_order	= document.getElementById('time_order')
const node_search	= document.getElementById('node_search')
const toggle_refresh	= document.getElementById('toggle_refresh')
const refresh_status	= document.getElementById('refresh_status')
const results_div	= document.getElementById('results_div')
const results_title	= document.getElementById('results_title')

// Global constants:
/**
 * Maximum number of events to show.
 */
const max_events = 100

/**
 * Integer that defines the refresh rate of the page, in milliseconds.
 */
const delay = 420

// Global variables:
/**
 * Holds the thread pointer to the refresh thread.
 */
var refresh_thread

/**
 * A boolean that indicates to the refresh thread if it should pause or not.
 */
var is_paused = false

/**
 * Boolean that holds the value if the refresh thread is in progress or not.
 * Even though the variable is_paused seems to do the same, this variable is crucial in preventing duplicate threads.
 */
var refresh_in_progress = false

/**
 * Only stays true while refreshing once.
 */
var refreshing_once = false

/**
 * Has the list of servers to be presented in share_host
 */
var share_host_list = []

/**
 * Saves previous session state.
 */
const state = {
	share_host	: "",
	share_name	: "",
	time_span	: "10m",// Does not set on first execution. Has to be set in tandem with "selected" attribute.
	user_search	: "",
	time_order	: "",
	node_search	: "",
	is_paused	: is_paused,
}

/**
 * Main function.
 */
function main() {
	// Reload previous session state:
	reload = JSON.parse(window.localStorage.getItem("state"))
	if(reload != null) {
		state.share_host = reload.share_host
		share_host.value = state.share_host
		state.share_name = reload.share_name
		share_name.value = state.share_name
		state.time_span	 = reload.time_span
		time_span.value	 = state.time_span
		state.user_search= reload.user_search
		user_search.value= state.user_search
		state.time_order = reload.time_order
		time_order.value = state.time_order
		state.node_search= reload.node_search
		node_search.value= state.node_search
		state.is_paused	 = reload.is_paused
		is_paused	 = state.is_paused
	}
	else {
		window.localStorage.setItem("state", JSON.stringify(state))
	}
	if (state.time_order == "DESC") {
		time_order_btn.innerHTML = "🔻 Most recent first"
	}
	else {
		time_order_btn.innerHTML = "🔺 Oldest first"
	}
	// Initiate refresh thread and present the current state in the UI:
	if(!is_paused) {
		toggle_refresh.innerHTML = "⏸️ Pause"
		refresh_status.innerHTML = "🔴 Live"
		toggle_refresh.classList.remove('btn-warning');
		toggle_refresh.classList.add('btn-success');
		if(!refresh_in_progress){
			refresh()
		}
		is_paused = false // Redundant, but stays here, just in case.
	}
	else {
		toggle_refresh.innerHTML = "▶️ Resume"
		refresh_status.innerHTML = "⚠️ Paused!"
		toggle_refresh.classList.remove('btn-success');
		toggle_refresh.classList.add('btn-warning');
	}
	// If it's paused, does just one refresh.
	if(is_paused) {
		refreshing_once = true
		setInterval(refresh_once, 2000)
	}
}

/**
 * Toggles the refresh thread between paused and running states.
 */
function toggle_refresh_thread() {
	// Update the status tracking variables:
	is_paused = !is_paused
	state.is_paused = is_paused
	// The server doesn't need to know if the thread is paused or not.
	// It only needs to be stored in LocalStorage, hence the following line.
	update_state()
	if(!is_paused) {
		toggle_refresh.innerHTML = "⏸️ Pause"
		refresh_status.innerHTML = "🔴 Live"
		toggle_refresh.classList.remove('btn-warning');
		toggle_refresh.classList.add('btn-success');
		if(!refresh_in_progress){
			refresh()
		}
		is_paused = false // Looks redundant, but stays here just in case.
	}
	else {
		toggle_refresh.innerHTML = "▶️ Resume"
		refresh_status.innerHTML = "⚠️ Paused!"
		toggle_refresh.classList.remove('btn-success');
		toggle_refresh.classList.add('btn-warning');
	}
}

/**
 * Refresh function
 */
function refresh(once = false) {
	// Before it starts updating, it should know if the order to stop was given:
	if(is_paused && !once) {
		refresh_in_progress = false
		clearInterval(refresh_thread)
		return
	}

	fetch("/ajax.html",
		{
			method: "POST", // Or "PUT"
			headers: {
				"Content-Type": "application/json"
			},
			body: JSON.stringify(state),
		}
	).then(
		response => response.json()
	).then(
		data => {
			display_results(data)
		}
	).catch(
		(error) => {
			console.error("Error:", error)
		}
	)

	// Only execute on the first thread iteration, in case it is not supposed to be a single refresh:
	if(!refresh_in_progress && !once) {
		refresh_in_progress = true
		refresh_thread = setInterval(refresh, delay) // This sets the recursion in motion
	}
}

/**
 * Toggles the time order
 */
function toggle_time_order() {
	if (state.time_order == "DESC") {
		time_order.value = "ASC"
		time_order_btn.innerHTML = "🔺 Oldest first"
	}
	else {
		time_order.value = "DESC"
		time_order_btn.innerHTML = "🔻 Most recent first"
	}
	update_state()
}

/**
 * This function is called at every input update
 */
function update_state() {
	state.share_host = share_host.value
	state.share_name = share_name.value
	state.time_span	 = time_span.value
	state.user_search= user_search.value
	state.time_order = time_order.value
	state.node_search= node_search.value
	state.is_paused	 = is_paused
	window.localStorage.setItem("state", JSON.stringify(state))

	// In case it's paused, it refreshes only once:
	if(is_paused) {
		refreshing_once = true
		setInterval(refresh_once, 2000)
	}
}

/**
 * As the name says
 */
function clear_filters(){
	node_search.value	= ""
	share_host.value	= ""
	share_name.value	= ""
	user_search.value	= ""
	time_order.value	= "DESC"
	time_order_btn.innerHTML = "🔻 Most recent first"
	//time_span.value	= "10m"
	update_state()
}

function reset_share_name() {
	share_name.value	= ""
	state.share_name	= ""
	window.localStorage.setItem("state", JSON.stringify(state))
}

function refresh_once(){
	if(refreshing_once){
		refreshing_once = false
		refresh(once = true)
	}
}

function display_results(data) {
	// share_host
	if (data['servers'].length > 0) {
		if (share_host_loading) {
			share_host_loading.remove()
		}
		for (const server of data['servers']) {
			if (!share_host_list.includes(server['share_host'])) {
				const option = document.createElement('option')
				option.value = server['share_host']
				option.textContent = server['share_host']
				share_host.appendChild(option)
				share_host_list.push(server['share_host'])
			}
		}
	}
	// share_name
	if (data['shares'].length > 0) {
		while (share_name.options.length > 1) {
			share_name.remove(1)
		}
		for (const share of data['shares']) {
			const option = document.createElement('option')
			option.value = share['share_name']//TODO share_id
			option.textContent = share['share_name']
			share_name.appendChild(option)
		}
	}
	else {
		while (share_name.options.length > 1) {
			share_name.remove(1)
		}
	}
	
	if(data['events'].length > 999){
		results_title.innerHTML = "Showing 999+ events:"
	}
	else if(data['events'].length < 1){
		results_title.innerHTML = "No events to show."
	}
	else{
		results_title.innerHTML = `Showing ${data['events'].length} events:`
	}
	result_string = ""
	for (const result of data['events']) {

		datetime = timeConverter(result["utc_timestamp"])

		if(result["event_type"] == 2){
			if(result["node1_name"] == result["node2_name"]){
				result_string += `
<div class="rounded border border-warning-subtlee" style="background-color: #440; border: #fff;margin: 3px; padding: 6px;">
	<div style="display: flex; justify-content: space-between; width: 100%;">
	<span>🗓️${datetime} 👨🏼‍💻${result["user_name"]}@${result["user_host"]}(${result["user_ip"]})</span>&nbsp;
	<span style="text-align: right;">☁️${result["share_host"]} 💿${result["share_name"]}</span>
	</div>
	⤵️Move: <span class="mono">${result["node1_name"]}</span><br>
	<hr style="margin: 0px; padding: 0px;">
	<span class="mono">${result["node1_path"]}<br>⬇️<br>
	${result["node2_path"]}</span>
</div>`
			} else {
				result_string += `
<div class="rounded border border-primary-subtle" style="background-color: #024; border: #fff;margin: 3px; padding: 6px;">
	<div style="display: flex; justify-content: space-between; width: 100%;">
	<span>🗓️${datetime} 👨🏼‍💻${result["user_name"]}@${result["user_host"]}(${result["user_ip"]})</span>&nbsp;
	<span style="text-align: right;">☁️${result["share_host"]} 💿${result["share_name"]}</span>
	</div>
	📝Rename: <span class="mono">${result["node1_name"]}</span> ➡️ <span class="mono">${result["node2_name"]}</span><br>
	<hr style="margin: 0px; padding: 0px;">
	<span class="mono">${result["node2_path"]}</span>
</div>`
			}
		}
		else if(result["event_type"] == 1){
			result_string += `
<div class="rounded border border-success-subtle" style="background-color: #240; border: #fff;margin: 3px; padding: 6px;">
	<div style="display: flex; justify-content: space-between; width: 100%;">
	<span>🗓️${datetime} 👨🏼‍💻${result["user_name"]}@${result["user_host"]}(${result["user_ip"]})</span>&nbsp;
	<span style="text-align: right;">☁️${result["share_host"]} 💿${result["share_name"]}</span>
	</div>
	📁Mkdir: <span class="mono">${result["node1_name"]}</span><br>
	<hr style="margin: 0px; padding: 0px;">
	<span class="mono">${result["node1_path"]}</span>
</div>`
		}
		else{
			result_string += `
<div class="rounded border border-secondary-subtle" style="background-color: #420; border: #fff;margin: 3px; padding: 6px;">
	<div style="display: flex; justify-content: space-between; width: 100%;">
	<span>🗓️${datetime} 👨🏼‍💻${result["user_name"]}@${result["user_host"]}(${result["user_ip"]})</span>&nbsp;
	<span style="text-align: right;">☁️${result["share_host"]} 💿${result["share_name"]}</span>
	</div>
	❌Unlink: <span class="mono">${result["node1_name"]}</span><br>
	<hr style="margin: 0px; padding: 0px;">
	<span class="mono">${result["node1_path"]}</span>
</div>`
		}
	}
	results_div.innerHTML = result_string

	share_host.value = state.share_host
	share_name.value = state.share_name
}

function timeConverter(UNIX_timestamp){
	var a = new Date(UNIX_timestamp * 1000);
	var months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
	var year = a.getFullYear();
	var month = months[a.getMonth()];
	var date = a.getDate();
	var hour = a.getHours();
	var min = a.getMinutes().toString().padStart(2, '0');
	var sec = a.getSeconds().toString().padStart(2, '0');
	var time = date + ' ' + month + ' ' + year + ' ⌚' + hour + ':' + min + ':' + sec ;
	return time;
}
