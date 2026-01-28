import React from "react";
import { Card, CardContent, Typography, Box } from "@mui/material";
import { TrendingUp, TrendingDown } from "@mui/icons-material";

export interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  color?: "primary" | "secondary" | "success" | "error" | "warning" | "info";
  icon?: React.ReactNode;
}

const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  color = "primary",
  icon,
}) => {
  const getTrendColor = () => {
    if (trend === "up") return "success.main";
    if (trend === "down") return "error.main";
    return "text.secondary";
  };

  const getTrendIcon = () => {
    if (trend === "up") return <TrendingUp sx={{ fontSize: 16 }} />;
    if (trend === "down") return <TrendingDown sx={{ fontSize: 16 }} />;
    return null;
  };

  return (
    <Card
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        transition: "transform 0.2s, box-shadow 0.2s",
        "&:hover": {
          transform: "translateY(-4px)",
          boxShadow: 4,
        },
      }}
    >
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          {icon && (
            <Box
              sx={{
                color: `${color}.main`,
                opacity: 0.7,
              }}
            >
              {icon}
            </Box>
          )}
        </Box>
        <Typography variant="h4" component="div" sx={{ fontWeight: "bold", mb: 1 }}>
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
        {trend && trendValue && (
          <Box sx={{ display: "flex", alignItems: "center", mt: 1, color: getTrendColor() }}>
            {getTrendIcon()}
            <Typography variant="caption" sx={{ ml: 0.5 }}>
              {trendValue}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default KpiCard;
