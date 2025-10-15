document.addEventListener('DOMContentLoaded', () => {
  const navbarToggler = document.querySelector('.tl-navbar-toggler');
  const navbarCollapse = document.querySelector('.tl-navbar-collapse');
  const togglerIcon = document.querySelector('.tl-toggler-icon');

  // Function to toggle visibility based on screen size
  function updateTogglerVisibility() {
    if (navbarToggler) {
      if (window.innerWidth >= 992) {
        navbarToggler.style.display = 'none';
      } else {
        navbarToggler.style.display = 'block';
      }
    }
  }

  // Initial check
  updateTogglerVisibility();

  // Update visibility on window resize
  window.addEventListener('resize', updateTogglerVisibility);

  // Toggle navbar collapse on click
  if (navbarToggler && navbarCollapse && togglerIcon) {
    navbarToggler.addEventListener('click', function () {
      navbarCollapse.classList.toggle('show');
      if (navbarCollapse.classList.contains('show')) {
        togglerIcon.classList.remove('bi-list');
        togglerIcon.classList.add('bi-x');
      } else {
        togglerIcon.classList.remove('bi-x');
        togglerIcon.classList.add('bi-list');
      }
    });
  }
  
  // Navbar scroll effect remains unchanged.
  window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
      if (window.scrollY > 10) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    }
  });
  
  // Set active nav-link based on current path.
  const currentPath = window.location.pathname;
  document.querySelectorAll('.tl-nav-link').forEach(link => {
    if(link.getAttribute('href') === currentPath){
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
});



