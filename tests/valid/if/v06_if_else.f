program ifelse
  integer x, y, max
  read *, x
  read *, y
  if (x .GT. y) then
    max = x
  else
    max = y
  endif
  print *, max
end
