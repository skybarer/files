var Andromeda = {

	showPage : function(path, targetDiv) {
		var jqxhr = jQuery.post(path, function(data) {
			jQuery("#" + targetDiv).html(data);
		});
	},
	
	bookSdcSlot	: function () {
		var path = "/sdc/html/general/sdcSlotBooking.html";
		Andromeda.showPage(path, "replaceDiv");
	},
	
	showIBMJunkCollegesData : function() {
		var path = "/sdc/html/SIP-General/IBMExtraCollegeDetails.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	getCollegesforReg : function(parameter) {
		Andromeda.setSessionValue("param", parameter);
		var path = "/sdc/html/SIP-General/ClientRegistration.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showSIPHome : function() {
		var path = "/sdc/html/SIP-General/SIPHome.html";
		Andromeda.showPage(path, "contentDiv");
	},

	showYearsPage : function() {
		var path = "/sdc/html/SIP-General/SIPYearwise.html";
		Andromeda.showPage(path, "contentDiv");
	},

	showCollegePrograms : function() {
		var path = "/sdc/html/SIP-General/SIPCollegeWisePrograms.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showFacultyPrograms : function() {
		var path = "/sdc/html/SIP-General/FacultyPrograms.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showPrograms : function() {
		var path = "/sdc/html/SIP-General/SIPPrograms.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showStudents : function() {
		var path = "/sdc/html/SIP-General/SIPStudents.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showCollegeDashboardPage : function() {
		var path = "/sdc/html/SIP-General/Dashboard.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showMentorsPage : function() {
		var path = "/sdc/html/SIP-General/Mentors.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showAttendancePage : function() {
		var path = "/sdc/html/SIP-General/AttendanceTrainingPrgms.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showAttendanceReportHomePage : function() {
		var path = "/sdc/html/SIP-General/AttendanceReport.html";
		Andromeda.showPage(path, "contentDiv");
	},

	showCollegeDetailsPage : function() {
		var path = "/sdc/html/SIP-General/CollegeDetails.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showAttReportTrainingPrgmsPage : function() {
		var path = "/sdc/html/SIP-General/AttReportTrainingPrgms.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showAttPrograms : function() {
		var path = "/sdc/html/SIP-General/AttendancePrgms.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showAttStudents : function() {
		var path = "/sdc/html/SIP-General/StudentAtt.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showAttReportPrgmsPage : function() {
		var path = "/sdc/html/SIP-General/AttReportPrgms.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showAttReportStudents : function() {
		var path = "/sdc/html/SIP-General/AttReportStudents.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	showFIPFacultyDetails : function() {
		var path = "/sdc/html/SIP-General/FIPFacultyDetails.html";
		Andromeda.showPage(path, "angularContentDiv");
	},

	/*
	 * getCollegesforReg : function() { var path =
	 * "/sdc/html/SIP-General/ClientRegistration.html"; Andromeda.showPage(path,
	 * "registrationDiv"); },
	 */

	showLinkGenerationPage : function() {
		var path = "/sdc/html/SIP-General/LinkGeneration.html";
		Andromeda.showPage(path, "contentDiv");
	},

	showStudentShiftPage : function() {
		var path = "/sdc/html/SIP-General/StudentShift.html";
		Andromeda.showPage(path, "contentDiv");
	},

	showCollegePaymentPage : function() {
		var path = "/sdc/html/SIP-General/CollegePayment.html";
		Andromeda.showPage(path, "contentDiv");
	},

	showCareers : function() {
		window.open("http://engineering.apssdc.in/careers/");
	},

	showRegistrationPage : function() {
		window.open("http://engineering.apssdc.in/studentSubscribe/");
	},

	showSIPRegistrationPage : function() {
		window.open("http://engineering.apssdc.in/register/");
	},

	showAlgCSE : function(key) {
		Andromeda.setSessionValue("key", key);
		$("#replaceDiv").load("/andromeda/html/general/Summer_Schedule_Details.html");
	},

	showSummerPrograms : function() {
		$("#replaceDiv").load("/andromeda/html/general/SummerSchedule.html");
	},
	
	showWorkshops : function() {
		$("#replaceDiv").load("/andromeda/html/general/Workshops.html");
	},

	showSIPPrograms : function() {
		$("#replaceDiv").load("/andromeda/html/general/SIPSchedule.html");
	},

	showSchedule : function() {
		$("#replaceDiv").load("/andromeda/html/general/Summer_Schedule.html");
	},

	showLoginPage : function() {
		$("#replaceDiv").load("/andromeda/html/login/loginForm.html");
	},

	showPressReleasesPage : function() {
		$("#replaceDiv").load("/andromeda/html/general/PressClippings.html");
	},

	showHomePage : function() {
		var path = "/andromeda/html/general/loginHome.html";
		Andromeda.showPage(path, "amdContainerDiv");
	},

	showReport : function() {
		var path = "/andromeda/html/general/Report.html";
		Andromeda.showPage(path, "replaceDiv");
		// $("#amdContainerDiv").load("/andromeda/html/general/home.html");
	},

	showMainPage : function() {
		var path = "/andromeda/html/general/Home.html";
		Andromeda.showPage(path, "amdContainerDiv");
	},

	showSlidePage : function() {
		$("#replaceDiv").load("/andromeda/html/general/Slideshow.html");
	},

	showAboutPage : function() {
		$("#replaceDiv").load("/andromeda/html/general/About.html");
	},

	showContactPage1 : function() {
		var path = "/andromeda/html/general/Summer_Contacts.html";
		Andromeda.showPage(path, "replaceDiv");
	},

	showPlacementsPage : function() {
		$("#replaceDiv").load("/andromeda/html/general/Placement.html");
	},

	showMediaPage : function() {
		var path = "/andromeda/html/general/Media.html";
		Andromeda.showPage(path, "replaceDiv1");
	},

	showEventsPage : function(academicYear) {
		Andromeda.setSessionValue("financialYear", academicYear);
		$("#replaceDiv").load("/andromeda/html/general/Events.html");
	},

	showSdcPage : function() {
		$("#replaceDiv").load("/andromeda/html/general/Sdc.html");
	},
	
	showCMsdcPage : function() {
		$("#replaceDiv").load("/andromeda/html/general/CMsdc.html");
	},

	showTrainingPrograms : function(type) {
		Andromeda.setSessionValue("programs", type);
		$("#replaceDiv").load("/andromeda/html/general/Training.html");
	},

	showPartners : function() {
		$("#replaceDiv").load("/andromeda/html/general/Partners.html");
	},

	showContactPage : function() {
		$("#replaceDiv").load("/andromeda/html/general/Contact.html");
	},

	showTestimonials : function() {
		$("#replaceDiv").load("/andromeda/html/general/Testimonials.html");
	},

	showFAQS : function() {
		$("#loginDiv").load("/andromeda/html/general/FAQS.html");
	},

	showAllProjects : function() {
		$("#loginDiv").load("/andromeda/html/login/Projects.html");
	},

	showUIF2Page : function() {
		var path = "/andromeda/html/general/UIF2Page.html";
		Andromeda.showPage(path, "replaceDiv");
	},

	showUIFUpload : function() {
		var path = "/andromeda/html/general/UIFUpload.html";
		Andromeda.showPage(path, "loginDiv");
	},

	showUIF2Gallery : function() {
		var path = "/andromeda/html/general/UIF2Gallery.html";
		Andromeda.showPage(path, "replaceDiv");
	},

	showPrivacyPolicyPage : function() {
		var path = "/andromeda/html/general/PrivacyPolicy.html";
		Andromeda.showPage(path, "replaceDiv");
	},

	showDashboardPage : function() {
		var path = "/reports/html/Dashboard/index.html";
		Andromeda.showPage(path, "amdContentDiv");
	},

	showCollegeDashboardPage : function() {
		var path = "/sip/html/general/SIPHome.html";
		Andromeda.showPage(path, "amdContainerDiv");
	},

	showClientPage : function() {
		var path = "/sip/html/general/ClientHome.html";
		Andromeda.showPage(path, "amdContainerDiv");
	},

	showTooplePage : function() {
		var path = "/sip/html/toople/Home.html";
		Andromeda.showPage(path, "amdContainerDiv");
	},

	showRedirectedPage : function() {
		window.open('http://engineering.apssdc.in/reports/', '_newtab');
	},

	home : function() {
		window.location.reload();
	},

	setSessionValue : function(key, value) {
		sessionStorage.setItem(key, value);
	},

	getSessionValue : function(key) {
		return sessionStorage.getItem(key);
	},

	removeSessionValue : function(key) {
		sessionStorage.removeItem(key);
	},

	showError : function(errorMessage) {
		var message = "<div class=\"alert alert-danger\"><center style='font-size: medium;'><strong>Error: </strong>"
				+ errorMessage + "</center></div>";
		jQuery("#errorDiv").html(message);
	},

	logout : function() {
		var username = Andromeda.getSessionValue("username") || "";
		Andromeda.setSessionValue("context", null);
		Andromeda.setSessionValue("collegeid", null);
		var data = {
			username : username
		};
		Andromeda.post('/andromeda/security/logout', data);
		Andromeda.showMainPage();
	},

	post : function(url, data) {
		var responseData = null;

		jQuery.ajax({
			url : url,
			type : 'post',
			data : JSON.stringify(data), // Stringified Json Object
			dataType : 'json',
			async : false, // Cross-domain requests and dataType: "jsonp"
			// requests do not support synchronous operation
			cache : false, // This will force requested pages not to be cached
			// by the browser
			processData : false, // To avoid making query String instead of
			// JSON
			contentType : "application/json; charset=utf-8",
			success : function(data) {
				responseData = data;
			}
		});

		return responseData;
	},

	isUserLoggedIn : function() {
		var username = Andromeda.getSessionValue("userName") || "";
		var context = Andromeda.getSessionValue("context") || "";
		var collegeid = Andromeda.getSessionValue("collegeid") || "";

		var login = {
			username : username,
			context : context,
			cliendId : collegeid
		};
		return Andromeda.post('/andromeda/security/loggedin', login) || false;
	},

	showModulesPage : function(userName) {
		var object = {
			userName : userName
		};
		var data = Andromeda.post('/andromeda/modules', object);
		Andromeda.showModules(data);
	},

	loadModule : function(userName, moduleId, moduleUrl) {
		Andromeda.setSessionValue("userName", userName);
		Andromeda.setSessionValue("moduleId", moduleId);
		jQuery("#amdContainerDiv").load(moduleUrl);
	},

	loadLink : function(path) {
		var targetDiv = "amdContentDiv";
		Andromeda.showPage(path, targetDiv);
	},

	showLinks : function(data) {
		var linksDataString = "No links present";
		if ((data) && (data.links) && (data.links.length > 0)) {
			// var moduleString = "<div id='sidebar' class='well sidebar-nav'>";
			var moduleString = "", moduleStringRep = "", moduleString360View = "", consolidatedString = "", single = "";
			for (var i = 0; i < data.links.length; i++) {
				var serviceId = data.links[i].id || "No ID";
				var serviceName = data.links[i].name || "No Name";
				var serviceDescription = data.links[i].description
						|| "No Description";
				var serviceUrl = data.links[i].url || "No Url";
				var serviceFunction = data.links[i].functionName
						|| "No Function";
				var parentId = parseInt(data.links[i].parentId);
				// var moduleTestUrl = data.modules[i].testUrl;
				// var userName = Andromeda.getSessionId("username");
				// "Andromeda.loadLink('" + serviceUrl + "');
				if (parentId == 1) {
					moduleString += "<li class='left-menu-item cursor-pointer' onClick='"
							+ serviceFunction
							+ "'><a>"
							+ serviceDescription
							+ "</a></li>";
				} else if (parentId == 2) {
					moduleStringRep += "<li class='left-menu-item cursor-pointer' onClick='"
							+ serviceFunction
							+ "'><a>"
							+ serviceDescription
							+ "</a></li>";
				} else if (parentId == 3) {
					moduleString360View += "<li class='left-menu-item cursor-pointer' onClick='"
						+ serviceFunction
						+ "'><a>"
						+ serviceDescription
						+ "</a></li>";
				} else if (parentId == 4) {
					consolidatedString += "<li class='left-menu-item cursor-pointer' onClick='"
						+ serviceFunction
						+ "'><a>"
						+ serviceDescription
						+ "</a></li>";
				} else {
					single += "<li class='left-menu-item cursor-pointer' onClick='"
							+ serviceFunction
							+ "'><a>"
							+ serviceDescription
							+ "</a></li>";
				}
			}
			linksDataString = moduleString;
		}
		jQuery("#amdContentDiv").html(linksDataString);
		jQuery("#amdContentDivRep").html(moduleStringRep);
		jQuery("#amdContentDiv360View").html(moduleString360View);
		jQuery("#amdContentDivConsolidated").html(consolidatedString);
		jQuery("#single").html(single);
	},

	loadServices : function() {
		var userName = Andromeda.getSessionValue("userName");
		var moduleId = Andromeda.getSessionValue("moduleId");
		var path = "/andromeda/moduleServices/" + userName + "/" + moduleId;
		var jqxhr = Andromeda.post(path, '');
		Andromeda.showLinks(jqxhr);
	},

	showModules : function(data) {
		var modulesDataString = "No modules present";
		if ((data) && (data.modules) && (data.modules.length > 0)) {
			modulesDataString = "<div class=\"row\">";
			for (var i = 0; i < data.modules.length; i++) {
				var moduleId = data.modules[i].id || "No ID";
				var moduleName = data.modules[i].name || "No Name";
				var moduleDescription = data.modules[i].description
						|| "No Description";
				var moduleUrl = data.modules[i].url || "No Url";
				var moduleTestUrl = data.modules[i].testUrl;
				var userName = Andromeda.getSessionValue("userName");
				var moduleString = "<div class=\"col-md-3 amdModuleDiv\" onClick=\"Andromeda.loadModule('"
						+ userName
						+ "',"
						+ moduleId
						+ ",'"
						+ moduleUrl
						+ "');\">";
				moduleString += "<div class=\"amdModule\" id=\"amdModuleId\"><table border=\"0\"><tr>";
				moduleString += "<td><div class=\"amdModuleIcon\"><img src='/andromeda/images/icons/"+moduleName+".png' alt='' /></div></td>";

				moduleString += "<td><div class=\"amdModuleTitle\">"
						+ moduleName + "</div></td>";
				moduleString += "</tr><tr><td colspan=\"2\">";
				moduleString += "<div class=\"amdModuleDescription\">"
						+ moduleDescription + "</div>";
				moduleString += "</td></tr></table></div></div>";

				modulesDataString += moduleString;
			}
			modulesDataString += "</div>";
		}
		jQuery("#amdContentDiv").html(modulesDataString);
	}
};
