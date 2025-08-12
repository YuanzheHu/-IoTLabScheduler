"""
Icon display fix utilities
解决Streamlit中Material Design Icons显示问题
"""

import streamlit as st


def apply_icon_fixes():
    """
    Apply CSS and JavaScript fixes for Material Design Icons display issues
    """
    st.markdown("""
    <style>
    /* Hide Material Design icon text fallbacks */
    [class*="material-icons"] {
        font-size: 0 !important;
    }

    /* Fix for expander icons specifically */
    .streamlit-expanderHeader [data-testid="stExpanderToggleIcon"] {
        display: none !important;
    }

    .streamlit-expanderHeader::before {
        content: "▶" !important;
        margin-right: 0.5rem !important;
        font-size: 14px !important;
        font-family: "Arial", sans-serif !important;
        display: inline-block !important;
    }

    .streamlit-expanderHeader[aria-expanded="true"]::before {
        content: "▼" !important;
    }
    </style>

    <script>
    // JavaScript fix for Material Design Icons
    setTimeout(function() {
        // Hide any elements containing keyboard_arrow_right
        const elements = document.querySelectorAll('*');
        elements.forEach(function(el) {
            if (el.textContent && el.textContent.includes('keyboard_arrow_right')) {
                el.style.display = 'none';
            }
            if (el.textContent && el.textContent.includes('keyboard_arrow_down')) {
                el.style.display = 'none';
            }
        });
        
        // Replace Material Icon classes
        const materialIcons = document.querySelectorAll('.material-icons');
        materialIcons.forEach(function(icon) {
            if (icon.textContent === 'keyboard_arrow_right') {
                icon.innerHTML = '▶';
                icon.style.fontSize = '14px';
            }
            if (icon.textContent === 'keyboard_arrow_down') {
                icon.innerHTML = '▼';
                icon.style.fontSize = '14px';
            }
        });
    }, 100);

    // Observe for new elements and fix them
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    const textContent = node.textContent || '';
                    if (textContent.includes('keyboard_arrow_right') || textContent.includes('keyboard_arrow_down')) {
                        node.style.display = 'none';
                    }
                }
            });
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    </script>
    """, unsafe_allow_html=True)
