program badcall
  integer x
  x = 0
  call twotimes(5)
  print *, x
end

integer function twotimes(n)
  integer n
  twotimes = n * 2
end
