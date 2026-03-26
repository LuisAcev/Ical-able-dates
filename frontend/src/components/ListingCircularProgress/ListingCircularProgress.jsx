import CircularProgress from "@mui/material/CircularProgress";

export const ListingCircularProgress = ({ size = 40, ...props }) => {
  return (
    <>
      <svg width={0} height={0}>
        <defs>
          <linearGradient id="my_gradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#1fb467e3" />
            <stop offset="100%" stopColor="#0a6a2ae0" />
          </linearGradient>
        </defs>
      </svg>
      <CircularProgress
        size={size}
        sx={{ "svg circle": { stroke: "url(#my_gradient)" } }}
        {...props}
      />
    </>
  );
};
