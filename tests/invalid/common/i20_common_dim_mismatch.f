program badcom
  integer x
  common /b/ x(10)
end

subroutine badcom2
  integer y
  common /b/ y(5)
end
