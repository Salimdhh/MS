document.addEventListener('DOMContentLoaded', function() {
    const desktopNavbar = document.getElementById('desktopNavbar');
    const mobileTopbar = document.getElementById('mobileTopbar');
    const hrFlowSidebar = document.getElementById('hrFlowSidebar');
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebarToggleBtn = document.getElementById('sidebarToggle'); // زر تصغير/تكبير الشريط الجانبي
    const body = document.body;

    // Handle Navbar scroll shadow
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            if (desktopNavbar) desktopNavbar.classList.add('scrolled');
            if (mobileTopbar) mobileTopbar.classList.add('scrolled');
        } else {
            if (desktopNavbar) desktopNavbar.classList.remove('scrolled');
            if (mobileTopbar) mobileTopbar.classList.remove('scrolled');
        }
    });

    // Toggle Sidebar on Mobile (Overlay)
    if (mobileMenuToggle && hrFlowSidebar) {
        mobileMenuToggle.addEventListener('click', function(e) {
            e.preventDefault();
            hrFlowSidebar.classList.toggle('open'); // 'open' class shows/hides overlay sidebar
            // Ensure desktop collapse state is removed if switching from desktop to mobile
            hrFlowSidebar.classList.remove('collapsed-sidebar');
            body.classList.remove('sidebar-is-collapsed');
        });
    }

    // Close mobile sidebar when clicking outside
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 992 && hrFlowSidebar && hrFlowSidebar.classList.contains('open')) {
            // Check if click is outside sidebar and toggle button
            if (!hrFlowSidebar.contains(e.target) && !mobileMenuToggle.contains(e.target)) {
                hrFlowSidebar.classList.remove('open');
            }
        }
    });

    // Toggle Sidebar on Desktop (Collapse)
    if (sidebarToggleBtn && hrFlowSidebar && body) {
        sidebarToggleBtn.addEventListener('click', function() {
            hrFlowSidebar.classList.toggle('collapsed-sidebar');
            body.classList.toggle('sidebar-is-collapsed');
        });
    }

    // Function to adjust visibility of Navbar/Topbar and sidebar collapse state based on screen size
    function manageLayoutForScreenSize() {
        if (window.innerWidth <= 992) {
            // Mobile view: hide desktop navbar, show mobile topbar
            if (desktopNavbar) desktopNavbar.style.display = 'none';
            if (mobileTopbar) mobileTopbar.style.display = 'flex';
            
            // Mobile sidebar behavior: always as overlay, not collapsed
            if (hrFlowSidebar) {
                hrFlowSidebar.classList.remove('collapsed-sidebar'); // Remove desktop collapse class
                hrFlowSidebar.classList.remove('open'); // Ensure it's closed by default on mobile load/resize
            }
            if (body.classList.contains('sidebar-is-collapsed')) {
                body.classList.remove('sidebar-is-collapsed'); // Remove desktop collapse class from body
            }

        } else {
            // Desktop view: show desktop navbar, hide mobile topbar
            if (desktopNavbar) desktopNavbar.style.display = 'flex'; // Changed from display = 'flex' to add class 'flex' for better CSS control
            if (mobileTopbar) mobileTopbar.style.display = 'none';
            
            // Desktop sidebar behavior: manage collapse state, always visible (not overlay)
            if (hrFlowSidebar) {
                hrFlowSidebar.classList.remove('open'); // Remove mobile overlay class
                // On desktop, we want the sidebar to respect its last state (collapsed or expanded)
                // So, no explicit removal of 'collapsed-sidebar' here unless you want it to always open on desktop resize.
                // If you want it to always be open by default on desktop, uncomment the following:
                // hrFlowSidebar.classList.remove('collapsed-sidebar');
                // body.classList.remove('sidebar-is-collapsed');
            }
            // Ensure body class is updated if sidebar is collapsed on desktop (handled by button click)
        }
    }

    // Initial call
    manageLayoutForScreenSize();

    // Debounced resize event listener
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(manageLayoutForScreenSize, 250);
    });

});