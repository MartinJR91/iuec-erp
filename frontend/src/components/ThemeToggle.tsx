import React from "react";
import { IconButton, Tooltip } from "@mui/material";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";

import { useThemeContext } from "../context/ThemeContext";

const ThemeToggle: React.FC = () => {
  const { darkMode, toggleDarkMode } = useThemeContext();
  const label = darkMode ? "Activer le thème clair" : "Activer le thème sombre";

  return (
    <Tooltip title={label}>
      <IconButton color="inherit" onClick={toggleDarkMode} aria-label={label}>
        {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
      </IconButton>
    </Tooltip>
  );
};

export default ThemeToggle;
