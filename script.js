// Small read-only explorer for the Flask API. The main Campus Connect UI is the
// separate frontend application.
const API = window.location.origin + "/api";

function byId(id) {
  return document.getElementById(id);
}

async function getJson(path) {
  const response = await fetch(API + path);
  if (!response.ok) throw new Error("Request failed: " + path);
  return response.json();
}

async function load() {
  const status = byId("status");
  try {
    const health = await getJson("/health");
    status.textContent = "API online - " + health.tables.length + " tables";
    status.className = "badge ok";
  } catch (error) {
    status.textContent = "API offline";
    status.className = "badge bad";
    return;
  }

  const stats = await getJson("/stats");
  byId("stat-students").textContent = stats.total_students;
  byId("stat-courses").textContent = stats.total_courses;
  byId("stat-enrollments").textContent = stats.total_enrollments;
  byId("stat-available").textContent = stats.available_courses;

  const students = await getJson("/students");
  byId("student-rows").innerHTML = students
    .map(function (student) {
      return (
        "<tr><td>" + student.student_number + "</td>" +
        "<td>" + student.first_name + " " + student.last_name + "</td>" +
        "<td>" + student.program + "</td>" +
        "<td>" + student.year_level + "</td></tr>"
      );
    })
    .join("");
}

load();
